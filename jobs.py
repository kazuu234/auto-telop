"""Background transcription job queue (sequential worker).

Multiple videos can be enqueued at once; they are processed one at a time
to avoid overloading the machine with concurrent Whisper runs. The GUI
polls :func:`list_jobs` to render live status/progress.
"""

import os
import threading
import queue as queue_mod


# Job status values
QUEUED = "queued"
PROCESSING = "processing"
DONE = "done"
ERROR = "error"


class _JobManager:
    def __init__(self):
        self._jobs = {}          # job_id -> dict
        self._order = []         # job_ids in submission order
        self._lock = threading.Lock()
        self._queue = queue_mod.Queue()
        self._worker = None
        self._counter = 0
        self._projects_dir = None

    def configure(self, projects_dir):
        self._projects_dir = projects_dir

    def _ensure_worker(self):
        # A single persistent daemon worker blocks on the queue forever.
        # Starting it once avoids a race where a timing-out worker could
        # strand a freshly-enqueued job.
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(target=self._run, daemon=True)
            self._worker.start()

    def submit(self, video_path):
        """Enqueue a video for transcription. Returns the job dict."""
        video_path = os.path.abspath(os.path.expanduser(video_path))
        base = os.path.splitext(os.path.basename(video_path))[0]
        with self._lock:
            self._counter += 1
            job_id = str(self._counter)
            job = {
                "id": job_id,
                "video_path": video_path,
                "base_name": base,
                "status": QUEUED,
                "stage": "順番待ち",
                "error": None,
            }
            self._jobs[job_id] = job
            self._order.append(job_id)
        self._queue.put(job_id)
        self._ensure_worker()
        return dict(job)

    def _set(self, job_id, **kwargs):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(kwargs)

    def _run(self):
        # Import here so importing this module stays lightweight.
        from transcribe import run_pipeline

        while True:
            job_id = self._queue.get()  # block until a job is available
            job = self._jobs.get(job_id)
            if not job:
                continue

            video_path = job["video_path"]
            base = job["base_name"]
            project_dir = os.path.join(self._projects_dir, base)

            self._set(job_id, status=PROCESSING, stage="文字起こし中")

            def progress(stage, _jid=job_id):
                self._set(_jid, stage=stage)

            try:
                run_pipeline(video_path, project_dir, progress_cb=progress)
                self._set(job_id, status=DONE, stage="完了")
            except Exception as e:  # noqa: BLE001 - report to UI
                self._set(job_id, status=ERROR, stage="エラー", error=str(e))
            finally:
                self._queue.task_done()

    def list_jobs(self):
        """Return active jobs (queued/processing) and recently finished ones."""
        with self._lock:
            return [dict(self._jobs[jid]) for jid in self._order]

    def clear_finished(self):
        """Drop done/error jobs from the tracked list."""
        with self._lock:
            keep = [
                jid for jid in self._order
                if self._jobs[jid]["status"] in (QUEUED, PROCESSING)
            ]
            self._jobs = {jid: self._jobs[jid] for jid in keep}
            self._order = keep


# Module-level singleton
manager = _JobManager()
