"""Single-process deployment. Job reservations and model locks live in this worker."""
bind = "127.0.0.1:8765"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 0
graceful_timeout = 30
max_requests = 0
preload_app = False
accesslog = "-"
errorlog = "-"
capture_output = True
forwarded_allow_ips = "127.0.0.1"
