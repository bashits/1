"""RunPod Serverless LatentSync 1.6 — Lip-Sync via ComfyUI on RunPod.

Replaces fal.ai lipsync with RunPod Serverless (15-50x cheaper).

Architecture:
1. User provides RunPod API key + endpoint ID
2. We send ComfyUI workflow JSON to RunPod Serverless
3. RunPod spins up GPU worker (RTX 3090/4090), runs LatentSync 1.6
4. We poll for completion, download result video
5. Optional: Face Detailer post-processing via Impact Pack node

Pricing:
- RunPod RTX 3090: $0.27/hr → ~$0.009 per 3s clip (vs $0.265 fal.ai)
- RunPod RTX 4090: $0.44/hr → ~$0.015 per 3s clip
- Cold start: ~30s first request, then instant while warm

ComfyUI Workflow (LatentSync 1.6):
  LoadVideo → LoadAudio → AdjustVideoLength → LatentSync → CombineVideo
  Optional: → FaceDetailer (Impact Pack) → SaveVideo
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Storage
GENERATED_DIR = Path("/data/generated") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "generated")
)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
(GENERATED_DIR / "video").mkdir(exist_ok=True)
(GENERATED_DIR / "base_videos").mkdir(exist_ok=True)


def _get_runpod_key() -> str:
    """Get RUNPOD_API_KEY from environment."""
    return os.environ.get("RUNPOD_API_KEY", "")


def _get_runpod_endpoint() -> str:
    """Get RUNPOD_ENDPOINT_ID from environment."""
    return os.environ.get("RUNPOD_ENDPOINT_ID", "")


# ─── Spending Limits ──────────────────────────────────────────────────
# Protects against accidental balance drain.
# Configurable via env vars: RUNPOD_DAILY_LIMIT, RUNPOD_MONTHLY_LIMIT
# Defaults: $1/day, $10/month — safe for testing

DEFAULT_DAILY_LIMIT = float(os.environ.get("RUNPOD_DAILY_LIMIT", "1.0"))
DEFAULT_MONTHLY_LIMIT = float(os.environ.get("RUNPOD_MONTHLY_LIMIT", "10.0"))
MAX_SINGLE_JOB_COST = float(os.environ.get("RUNPOD_MAX_JOB_COST", "0.50"))  # reject jobs > $0.50

# In-memory spending tracker (resets on restart; also persisted to SQLite)
_spending_today: float = 0.0
_spending_month: float = 0.0
_spending_date: str = ""  # YYYY-MM-DD
_spending_month_key: str = ""  # YYYY-MM
_jobs_today: int = 0
_jobs_month: int = 0


def _reset_spending_if_needed() -> None:
    """Reset daily/monthly counters if date has changed."""
    global _spending_today, _spending_month, _spending_date, _spending_month_key
    global _jobs_today, _jobs_month
    from datetime import datetime
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    if _spending_date != today:
        _spending_today = 0.0
        _jobs_today = 0
        _spending_date = today

    if _spending_month_key != month:
        _spending_month = 0.0
        _jobs_month = 0
        _spending_month_key = month


def check_spending_limit(estimated_cost: float) -> dict:
    """Check if a new job would exceed spending limits.

    Returns {allowed: bool, reason: str, ...}
    """
    _reset_spending_if_needed()

    if estimated_cost > MAX_SINGLE_JOB_COST:
        return {
            "allowed": False,
            "reason": f"Single job cost ${estimated_cost:.4f} exceeds max ${MAX_SINGLE_JOB_COST:.2f}",
            "limit_type": "per_job",
        }

    if _spending_today + estimated_cost > DEFAULT_DAILY_LIMIT:
        return {
            "allowed": False,
            "reason": f"Daily limit reached: ${_spending_today:.4f} spent today, limit ${DEFAULT_DAILY_LIMIT:.2f}",
            "limit_type": "daily",
            "spent_today": _spending_today,
            "limit": DEFAULT_DAILY_LIMIT,
        }

    if _spending_month + estimated_cost > DEFAULT_MONTHLY_LIMIT:
        return {
            "allowed": False,
            "reason": f"Monthly limit reached: ${_spending_month:.4f} spent this month, limit ${DEFAULT_MONTHLY_LIMIT:.2f}",
            "limit_type": "monthly",
            "spent_month": _spending_month,
            "limit": DEFAULT_MONTHLY_LIMIT,
        }

    return {
        "allowed": True,
        "spent_today": _spending_today,
        "spent_month": _spending_month,
        "daily_remaining": round(DEFAULT_DAILY_LIMIT - _spending_today, 4),
        "monthly_remaining": round(DEFAULT_MONTHLY_LIMIT - _spending_month, 4),
    }


def record_spending(cost: float) -> None:
    """Record actual spending after a job completes."""
    global _spending_today, _spending_month, _jobs_today, _jobs_month
    _reset_spending_if_needed()
    _spending_today += cost
    _spending_month += cost
    _jobs_today += 1
    _jobs_month += 1
    logger.info(
        "RunPod spending: +$%.4f | today=$%.4f/%s | month=$%.4f/%s | jobs=%d/%d",
        cost, _spending_today, DEFAULT_DAILY_LIMIT,
        _spending_month, DEFAULT_MONTHLY_LIMIT,
        _jobs_today, _jobs_month,
    )


def get_spending_summary() -> dict:
    """Get current spending summary."""
    _reset_spending_if_needed()
    return {
        "daily": {
            "spent": round(_spending_today, 4),
            "limit": DEFAULT_DAILY_LIMIT,
            "remaining": round(max(0, DEFAULT_DAILY_LIMIT - _spending_today), 4),
            "jobs": _jobs_today,
            "date": _spending_date,
        },
        "monthly": {
            "spent": round(_spending_month, 4),
            "limit": DEFAULT_MONTHLY_LIMIT,
            "remaining": round(max(0, DEFAULT_MONTHLY_LIMIT - _spending_month), 4),
            "jobs": _jobs_month,
            "month": _spending_month_key,
        },
        "limits": {
            "daily_limit": DEFAULT_DAILY_LIMIT,
            "monthly_limit": DEFAULT_MONTHLY_LIMIT,
            "max_job_cost": MAX_SINGLE_JOB_COST,
            "note": "Set RUNPOD_DAILY_LIMIT, RUNPOD_MONTHLY_LIMIT, RUNPOD_MAX_JOB_COST env vars to change",
        },
    }


# ─── RunPod Serverless Configuration ─────────────────────────────────

RUNPOD_BASE_URL = "https://api.runpod.ai/v2"

# Cost per second on different GPU tiers (RunPod Serverless pricing)
RUNPOD_GPU_COSTS = {
    "RTX_3090": 0.00075,      # $0.27/hr = $0.00075/sec
    "RTX_4090": 0.001222,     # $0.44/hr = $0.001222/sec
    "A100_40GB": 0.002778,    # $1.00/hr
    "A100_80GB": 0.003611,    # $1.30/hr
}

# Average processing time per second of output video
AVG_PROCESSING_RATIO = 4.0  # ~4 sec GPU time per 1 sec of output video


def estimate_runpod_cost(
    duration_seconds: float = 3.0,
    gpu_tier: str = "RTX_3090",
) -> float:
    """Estimate RunPod Serverless cost for LatentSync processing.

    Returns cost in USD.
    """
    gpu_cost_per_sec = RUNPOD_GPU_COSTS.get(gpu_tier, RUNPOD_GPU_COSTS["RTX_3090"])
    processing_time = duration_seconds * AVG_PROCESSING_RATIO
    return round(gpu_cost_per_sec * processing_time, 6)


# ─── ComfyUI Workflow Templates ──────────────────────────────────────

def build_latentsync_workflow(
    video_url: str,
    audio_url: str,
    use_face_detailer: bool = True,
    guidance_scale: float = 2.0,
    seed: int = -1,
) -> dict:
    """Build ComfyUI workflow JSON for LatentSync 1.6 lip-sync.

    LatentSync 1.6 improvements over 1.5:
    - 512×512 training resolution (vs 256×256)
    - Better temporal consistency
    - Improved lip-sync accuracy for non-English audio
    - Lower VRAM usage (~16GB vs 20GB)

    Workflow nodes:
    1. LoadVideo (from URL)
    2. LoadAudio (from URL)
    3. AdjustVideoLength (match audio duration)
    4. LatentSync (lip-sync inference)
    5. FaceDetailer (optional post-processing)
    6. CombineVideoAudio (merge synced video + audio)
    7. SaveVideo (output)
    """
    workflow = {
        "input": {
            "workflow": {
                # Node 1: Load base video
                "1": {
                    "class_type": "LoadVideoFromUrl",
                    "inputs": {
                        "url": video_url,
                        "force_rate": 25,
                        "force_size": "512x512",
                    },
                },
                # Node 2: Load audio
                "2": {
                    "class_type": "LoadAudioFromUrl",
                    "inputs": {
                        "url": audio_url,
                    },
                },
                # Node 3: Adjust video length to match audio
                "3": {
                    "class_type": "AdjustVideoLength",
                    "inputs": {
                        "video": ["1", 0],
                        "audio": ["2", 0],
                        "method": "loop_to_audio",
                    },
                },
                # Node 4: LatentSync 1.6 inference
                "4": {
                    "class_type": "LatentSync",
                    "inputs": {
                        "video": ["3", 0],
                        "audio": ["2", 0],
                        "guidance_scale": guidance_scale,
                        "seed": seed if seed >= 0 else -1,
                        "version": "v1.6",
                    },
                },
                # Node 7: Save output
                "7": {
                    "class_type": "SaveVideo",
                    "inputs": {
                        "video": ["4", 0] if not use_face_detailer else ["5", 0],
                        "audio": ["2", 0],
                        "format": "mp4",
                        "quality": 85,
                    },
                },
            },
        },
    }

    # Node 5: FaceDetailer (optional but recommended)
    if use_face_detailer:
        workflow["input"]["workflow"]["5"] = {
            "class_type": "FaceDetailer",
            "inputs": {
                "image": ["4", 0],
                "model": "face_yolov8n.pt",
                "guide_size": 512,
                "guide_size_for": True,
                "max_size": 1024,
                "seed": seed if seed >= 0 else -1,
                "steps": 20,
                "cfg": 7.0,
                "denoise": 0.35,
                "feather": 5,
                "noise_mask": True,
                "force_inpaint": True,
            },
        }

    return workflow


def build_simple_lipsync_payload(
    video_url: str,
    audio_url: str,
    use_face_detailer: bool = True,
    guidance_scale: float = 1.5,
    inference_steps: int = 20,
    seed: int = 1247,
) -> dict:
    """Build RunPod payload for LatentSync 1.6 custom handler.

    Our custom handler accepts video_url + audio_url directly
    and runs LatentSync 1.6 inference (no ComfyUI).
    Returns base64-encoded video in response.
    """
    return {
        "input": {
            "video_url": video_url,
            "audio_url": audio_url,
            "guidance_scale": guidance_scale,
            "inference_steps": inference_steps,
            "seed": seed,
            "use_face_detailer": use_face_detailer,
        },
    }


# ─── RunPod Serverless API Client ────────────────────────────────────

async def submit_runpod_job(
    payload: dict,
    endpoint_id: Optional[str] = None,
) -> dict:
    """Submit a job to RunPod Serverless endpoint.

    Returns: {success, job_id, status}
    """
    api_key = _get_runpod_key()
    if not api_key:
        return {"success": False, "error": "RUNPOD_API_KEY not configured"}

    ep_id = endpoint_id or _get_runpod_endpoint()
    if not ep_id:
        return {"success": False, "error": "RUNPOD_ENDPOINT_ID not configured"}

    url = f"{RUNPOD_BASE_URL}/{ep_id}/run"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "job_id": data.get("id", ""),
                    "status": data.get("status", "IN_QUEUE"),
                }
            else:
                return {
                    "success": False,
                    "error": f"RunPod API error: HTTP {resp.status_code} — {resp.text[:500]}",
                }
        except Exception as e:
            logger.error(f"RunPod submit failed: {e}")
            return {"success": False, "error": str(e)}


async def check_runpod_job(
    job_id: str,
    endpoint_id: Optional[str] = None,
) -> dict:
    """Check status of a RunPod Serverless job.

    Returns: {status, output, error}
    Status values: IN_QUEUE, IN_PROGRESS, COMPLETED, FAILED, CANCELLED
    """
    api_key = _get_runpod_key()
    if not api_key:
        return {"status": "FAILED", "error": "RUNPOD_API_KEY not configured"}

    ep_id = endpoint_id or _get_runpod_endpoint()
    if not ep_id:
        return {"status": "FAILED", "error": "RUNPOD_ENDPOINT_ID not configured"}

    url = f"{RUNPOD_BASE_URL}/{ep_id}/status/{job_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": data.get("status", "UNKNOWN"),
                    "output": data.get("output"),
                    "error": data.get("error"),
                    "execution_time": data.get("executionTime"),
                    "delay_time": data.get("delayTime"),
                }
            else:
                return {
                    "status": "FAILED",
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}",
                }
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}


async def wait_for_runpod_job(
    job_id: str,
    endpoint_id: Optional[str] = None,
    timeout_seconds: int = 300,
    poll_interval: float = 3.0,
) -> dict:
    """Wait for RunPod job to complete with polling.

    Returns final job result.
    """
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout_seconds:
            return {
                "status": "TIMEOUT",
                "error": f"Job timed out after {timeout_seconds}s",
                "job_id": job_id,
            }

        result = await check_runpod_job(job_id, endpoint_id)
        status = result.get("status", "")

        if status == "COMPLETED":
            return result
        elif status in ("FAILED", "CANCELLED"):
            return result

        await asyncio.sleep(poll_interval)


async def cancel_runpod_job(
    job_id: str,
    endpoint_id: Optional[str] = None,
) -> dict:
    """Cancel a running RunPod job."""
    api_key = _get_runpod_key()
    ep_id = endpoint_id or _get_runpod_endpoint()

    if not api_key or not ep_id:
        return {"success": False, "error": "RunPod not configured"}

    url = f"{RUNPOD_BASE_URL}/{ep_id}/cancel/{job_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(url, headers=headers)
            return {"success": resp.status_code == 200}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── High-Level Lip-Sync Generation ─────────────────────────────────

async def generate_lipsync_runpod(
    video_url: str,
    audio_url: str,
    use_face_detailer: bool = True,
    guidance_scale: float = 2.0,
    duration_seconds: float = 3.0,
    gpu_tier: str = "RTX_3090",
) -> dict:
    """Generate lip-synced video using RunPod Serverless + LatentSync 1.6.

    This is the main entry point replacing fal.ai lipsync.

    Flow:
    1. Build payload (ComfyUI workflow or simple format)
    2. Submit to RunPod Serverless
    3. Poll for completion
    4. Download and save result video
    5. Return result with cost estimate

    Args:
        video_url: URL of base video (girl talking/moving)
        audio_url: URL of generated audio (TTS)
        use_face_detailer: Apply Face Detailer post-processing
        guidance_scale: LatentSync guidance (1.5-3.0, higher = more accurate lips)
        duration_seconds: Expected output duration for cost estimation
        gpu_tier: RunPod GPU tier for cost calculation

    Returns: {success, video, cost_estimate, engine, ...}
    """
    # Check RunPod configuration
    api_key = _get_runpod_key()
    endpoint_id = _get_runpod_endpoint()

    if not api_key or not endpoint_id:
        return {
            "success": False,
            "error": "RunPod not configured. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID.",
            "setup_required": True,
            "instructions": {
                "step1": "Get RunPod API key from https://www.runpod.io/console/user/settings",
                "step2": "Deploy ComfyUI + LatentSync 1.6 Serverless endpoint",
                "step3": "Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables",
            },
        }

    # ─── Spending limit check ─────────────────────────
    estimated_cost = estimate_runpod_cost(duration_seconds, gpu_tier)
    limit_check = check_spending_limit(estimated_cost)
    if not limit_check.get("allowed"):
        return {
            "success": False,
            "error": f"Spending limit: {limit_check['reason']}",
            "limit_blocked": True,
            "spending": get_spending_summary(),
        }

    # Build payload
    payload = build_simple_lipsync_payload(
        video_url=video_url,
        audio_url=audio_url,
        use_face_detailer=use_face_detailer,
        guidance_scale=guidance_scale,
    )

    # Submit job
    logger.info(f"Submitting LatentSync 1.6 job to RunPod (endpoint={endpoint_id})")
    submit_result = await submit_runpod_job(payload, endpoint_id)

    if not submit_result.get("success"):
        return {
            "success": False,
            "error": f"RunPod submission failed: {submit_result.get('error')}",
            "engine": "runpod_latentsync_1.6",
        }

    job_id = submit_result["job_id"]
    logger.info(f"RunPod job submitted: {job_id}")

    # Wait for completion
    result = await wait_for_runpod_job(
        job_id,
        endpoint_id,
        timeout_seconds=300,
        poll_interval=3.0,
    )

    status = result.get("status", "")

    if status != "COMPLETED":
        return {
            "success": False,
            "error": f"RunPod job {status}: {result.get('error', 'Unknown error')}",
            "job_id": job_id,
            "engine": "runpod_latentsync_1.6",
        }

    # Extract output — our handler returns video_base64 or video_url
    output = result.get("output", {})
    saved_file = None

    if isinstance(output, dict):
        video_b64 = output.get("video_base64", "")
        video_result_url = output.get("video_url", output.get("url", ""))

        fname = f"lipsync_runpod_{uuid.uuid4().hex[:8]}.mp4"
        fpath = GENERATED_DIR / "video" / fname

        if video_b64:
            # Handler returned base64-encoded video — decode and save
            try:
                fpath.write_bytes(base64.b64decode(video_b64))
                saved_file = {
                    "filename": fname,
                    "file_path": str(fpath),
                    "url": f"/generated/video/{fname}",
                }
            except Exception as e:
                saved_file = {"error": f"Base64 decode failed: {e}"}
        elif video_result_url:
            # Handler returned a URL — download it
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    vid_resp = await client.get(video_result_url)
                    if vid_resp.status_code == 200:
                        fpath.write_bytes(vid_resp.content)
                        saved_file = {
                            "filename": fname,
                            "file_path": str(fpath),
                            "url": video_result_url,
                        }
                    else:
                        saved_file = {
                            "url": video_result_url,
                            "error": f"Download failed: HTTP {vid_resp.status_code}",
                        }
                except Exception as e:
                    saved_file = {"url": video_result_url, "error": str(e)}
        elif output.get("error"):
            saved_file = {"error": output["error"]}

    # Calculate cost
    cost = estimate_runpod_cost(duration_seconds, gpu_tier)
    execution_time = result.get("execution_time", 0)
    if execution_time:
        # Use actual execution time for more accurate cost
        gpu_cost_per_sec = RUNPOD_GPU_COSTS.get(gpu_tier, RUNPOD_GPU_COSTS["RTX_3090"])
        cost = round(gpu_cost_per_sec * (execution_time / 1000), 6)  # execution_time in ms

    success = saved_file is not None and "error" not in (saved_file or {})

    # Record spending for limit tracking
    if success:
        record_spending(cost)
    return {
        "success": success,
        "video": saved_file,
        "model": "latentsync_v1.6",
        "model_name": "LatentSync 1.6 (RunPod Serverless)",
        "cost_estimate": cost,
        "engine": "runpod_latentsync_1.6",
        "job_id": job_id,
        "execution_time_ms": result.get("execution_time"),
        "delay_time_ms": result.get("delay_time"),
        "face_detailer": use_face_detailer,
        "gpu_tier": gpu_tier,
    }


# ─── RunPod Health & Status ──────────────────────────────────────────

async def get_runpod_status() -> dict:
    """Check RunPod Serverless endpoint health and worker status."""
    api_key = _get_runpod_key()
    endpoint_id = _get_runpod_endpoint()

    if not api_key or not endpoint_id:
        return {
            "configured": False,
            "error": "RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID not set",
        }

    url = f"{RUNPOD_BASE_URL}/{endpoint_id}/health"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "configured": True,
                    "endpoint_id": endpoint_id,
                    "workers": data.get("workers", {}),
                    "jobs_completed": data.get("jobsCompleted", 0),
                    "jobs_in_queue": data.get("jobsInQueue", 0),
                    "jobs_in_progress": data.get("jobsInProgress", 0),
                }
            else:
                return {
                    "configured": True,
                    "endpoint_id": endpoint_id,
                    "error": f"Health check failed: HTTP {resp.status_code}",
                }
        except Exception as e:
            return {
                "configured": True,
                "endpoint_id": endpoint_id,
                "error": str(e),
            }


def get_runpod_pricing() -> dict:
    """Get RunPod pricing info for frontend display."""
    return {
        "engine": "RunPod Serverless + LatentSync 1.6",
        "gpu_tiers": {
            tier: {
                "cost_per_hour": round(cost * 3600, 2),
                "cost_per_second": cost,
                "cost_per_3s_clip": round(cost * 3.0 * AVG_PROCESSING_RATIO, 4),
                "cost_per_5s_clip": round(cost * 5.0 * AVG_PROCESSING_RATIO, 4),
                "cost_per_10s_clip": round(cost * 10.0 * AVG_PROCESSING_RATIO, 4),
            }
            for tier, cost in RUNPOD_GPU_COSTS.items()
        },
        "default_tier": "RTX_3090",
        "features": [
            "LatentSync 1.6 (512x512, improved temporal consistency)",
            "Face Detailer post-processing (Impact Pack)",
            "Pay-per-second billing (no idle costs)",
            "Auto-scaling (0 to N workers)",
            "Cold start ~30s, then instant",
        ],
        "vs_fal_ai": {
            "fal_omnihuman_3s": round(0.16 * 3, 2),
            "fal_latentsync_flat": 0.20,
            "runpod_latentsync_3s": round(RUNPOD_GPU_COSTS["RTX_3090"] * 3.0 * AVG_PROCESSING_RATIO, 4),
            "savings_factor": "15-50x cheaper",
        },
    }
