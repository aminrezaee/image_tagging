import tagserver
print("starting server")
server = tagserver.TagServer('example_config.yaml')
server.start()
