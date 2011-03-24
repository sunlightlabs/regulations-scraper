def patch_selenium_chrome():
    from selenium.webdriver.chrome import driver
    from gevent.http import HTTPServer
    from gevent.queue import Queue
    import time
    import urllib
    import json
    import subprocess
    
    # Patch to replace the command-and-control with one based on gevent, so it
    #  plays nicely with the rest of the stack
    def get_handle(command_queue, result_queue):
        def handle(request):
            if request.typestr == 'GET':
                request.add_output_header('Content-Type', 'text/html')
                request.send_reply(200, "OK", driver.INITIAL_HTML)
            elif request.typestr == 'POST':
                request.add_output_header('Content-Type', 'application/json')
                
                lines = []
                for line in request.input_buffer.readlines():
                    if line.strip() == "EOResponse":
                        break
                    lines.append(line)
                data = "".join(lines).strip()
                if data:
                    result_queue.put(json.loads(data))
                
                command = command_queue.get()
                data = json.dumps(command)
                request.send_reply(200, "OK", data)
        return handle
        
    def run_server(timeout=10):
        command_queue = Queue()
        result_queue = Queue()
        
        handle = get_handle(command_queue, result_queue)
        server = HTTPServer(("", 0), handle)
        
        server.command_queue = command_queue
        server.result_queue = result_queue
        
        greenlet = server.start()
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                urllib.urlopen("http://localhost:%s" % server.server_port).read()
                break
            except IOError:
                print "caught"
                time.sleep(0.1)
        else:
            raise driver.RemoteDriverServerException("Can't open server after %s seconds" % timeout)
        return server
    
    driver.run_server = run_server
    
    # Patch to replace the run_chrome command to shut it up so it doesn't pipe
    #  random crap to stdout and stderr
    def run_chrome(extension_dir, profile_dir, port, untrusted_certificates, custom_args):
        command = [
            driver.chrome_exe(),
            "--load-extension=%s" % extension_dir,
            "--user-data-dir=%s" % profile_dir,
            "--activate-on-launch",
            "--disable-hang-monitor",
            "--homepage=about:blank",
            "--no-first-run",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--no-default-browser-check",
            "http://localhost:%s/chromeCommandExecutor" % port,
            untrusted_certificates,
            custom_args,
        ]
        return subprocess.Popen(command, stdin=open("/dev/null", "r"), stdout=open("/dev/null", "w"), stderr=subprocess.STDOUT)
    
    driver.run_chrome = run_chrome