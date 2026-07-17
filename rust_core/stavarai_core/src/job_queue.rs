//! In-memory FIFO job queue with status tracking.
//!
//! Designed for pipeline tasks (video gen, scraping, scoring) that must not
//! block the API request thread. Workers poll [`JobQueue::dequeue`].
//! For persistence across restarts, snapshot via [`JobQueue::snapshot`] and
//! restore on boot — left as an exercise for the VPS deployment.

use base64::Engine;
use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn fresh_id() -> String {
    let mut bytes = [0u8; 16];
    OsRng.fill_bytes(&mut bytes);
    base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(&bytes)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "data")]
pub enum JobStatus {
    Pending,
    Running,
    Completed,
    Failed(String),
}

impl std::fmt::Display for JobStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            JobStatus::Pending => write!(f, "Pending"),
            JobStatus::Running => write!(f, "Running"),
            JobStatus::Completed => write!(f, "Completed"),
            JobStatus::Failed(r) => write!(f, "Failed({r})"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Job {
    pub id: String,
    pub job_type: String,
    pub payload: serde_json::Value,
    pub status: JobStatus,
    pub created_at: u64,
    pub started_at: Option<u64>,
    pub completed_at: Option<u64>,
}

pub struct JobQueue {
    queue: Mutex<VecDeque<Job>>,
    jobs: Mutex<HashMap<String, Job>>,
}

impl JobQueue {
    pub fn new() -> Self {
        Self {
            queue: Mutex::new(VecDeque::new()),
            jobs: Mutex::new(HashMap::new()),
        }
    }

    /// Enqueue a new job; returns its id.
    pub fn enqueue(&self, job_type: &str, payload: serde_json::Value) -> String {
        let id = fresh_id();
        let job = Job {
            id: id.clone(),
            job_type: job_type.to_string(),
            payload,
            status: JobStatus::Pending,
            created_at: now_secs(),
            started_at: None,
            completed_at: None,
        };
        self.queue.lock().expect("queue mutex poisoned").push_back(job.clone());
        self.jobs.lock().expect("jobs mutex poisoned").insert(id.clone(), job);
        id
    }

    /// Pop the next pending job and mark it Running.
    pub fn dequeue(&self) -> Option<Job> {
        let mut queue = self.queue.lock().expect("queue mutex poisoned");
        let mut job = queue.pop_front()?;
        let now = now_secs();
        job.status = JobStatus::Running;
        job.started_at = Some(now);
        self.jobs
            .lock()
            .expect("jobs mutex poisoned")
            .insert(job.id.clone(), job.clone());
        Some(job)
    }

    /// Mark a running job completed.
    pub fn complete(&self, id: &str) {
        self.set_terminal(id, JobStatus::Completed);
    }

    /// Mark a running job failed with a reason.
    pub fn fail(&self, id: &str, reason: &str) {
        self.set_terminal(id, JobStatus::Failed(reason.to_string()));
    }

    fn set_terminal(&self, id: &str, status: JobStatus) {
        let mut jobs = self.jobs.lock().expect("jobs mutex poisoned");
        if let Some(job) = jobs.get_mut(id) {
            job.status = status;
            job.completed_at = Some(now_secs());
        }
    }

    /// Look up the current status of a job.
    pub fn status(&self, id: &str) -> Option<JobStatus> {
        self.jobs
            .lock()
            .expect("jobs mutex poisoned")
            .get(id)
            .map(|j| j.status.clone())
    }

    /// Return all jobs (for dashboards / inspection).
    pub fn snapshot(&self) -> Vec<Job> {
        self.jobs
            .lock()
            .expect("jobs mutex poisoned")
            .values()
            .cloned()
            .collect()
    }
}

impl Default for JobQueue {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn enqueue_dequeue() {
        let q = JobQueue::new();
        let id = q.enqueue("t", json!({}));
        let job = q.dequeue().unwrap();
        assert_eq!(job.id, id);
        assert_eq!(job.status, JobStatus::Running);
    }
}
