import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
bind = "0.0.0.0:7000"  # Listen on all interfaces
timeout = 120
accesslog = '-'  # Log to stdout for debugging
errorlog = '-'   # Log to stderr for debugging