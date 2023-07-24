import speedtest


def test_server_speed():
    servers = []
    # If you want to test against a specific server
    # servers = [1234]

    s = speedtest.Speedtest()
    s.get_servers(servers)
    s.get_best_server()
    s.download()
    s.upload()
    #s.results.share()

    results_dict = s.results.dict()
    return results_dict

