from RemoteHttpGenerator import RemoteHttpGenerator

          
if __name__ == "__main__":
    http_generator = RemoteHttpGenerator()
    http_generator.initialise_remote_http_generator("vcenter.phantom.net", "tfuser", "password123.", "Testnet 3845 - CentOS - Traffic Tester", "user", "password")
    http_generator.remote_generate_http_traffic("http://58.58.12.1/Pages/default.php", "Testnet 3845", 50)
