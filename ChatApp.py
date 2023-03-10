import argparse
from socket import *
import threading

"""
GENERAL UTILITIES
"""
BUFFER_SIZE = 4096

def validate_args(args, parser):
  # TODO: other validations - IP address

  # Port number should be an integer value in the range 1024-65535. 
  ports = []
  if args.server:
    ports.append(getattr(args, "port"))
  else:
    ports.append(getattr(args, "server-port"))
    ports.append(getattr(args, "client-udp-port"))
    ports.append(getattr(args, "client-tcp-port"))
  for port in ports:
    if port < 1024 or port > 65535: # TODO: inclusive exclusive
      raise parser.error("Port number should be an integer value in the range 1024-65535")
  return

"""
Functionality for FileClient
"""

class FileClient:
  """
  Instance variables:
  name: Client name, username for this client in this file-sharing network
  server_ip: Server IP address
  server_port: Port that client sends UDP messages to the server
  client_udp_port: Port that client listens on for communication with the server
  client_tcp_port: Port that client listens for TCP connection requests from other clients for file transfers
  """

  def __init__(self, args):
    self.name = getattr(args, "name")
    self.server_ip = getattr(args, "server-ip")
    self.server_port = getattr(args, "server-port")
    self.client_udp_port = getattr(args, "client-udp-port")
    self.client_tcp_port = getattr(args, "client-tcp-port")

    self.client_socket = self.create_socket()
    self.local_table = {}
    return
  
  def create_socket(self):
    return socket(AF_INET, SOCK_DGRAM)
  
  def register(self):
    """
    Sends a UDP message to the server to register the client.
    """
    register_message = f"Registering {self.name}"
    self.client_socket.sendto(register_message.encode(),(self.server_ip, self.server_port))
    welcome_message, server_address = self.client_socket.recvfrom(BUFFER_SIZE)
    print(welcome_message.decode())
    self.client_socket.close()
    return
  
  def get_client_table(self):
    """
    Sends a UDP message to the server to get the client table.
    """
    # get_table_message = f"Getting client table"
    # self.client_socket.sendto(message.encode(),(self.server_ip, self.server_port))
    # modified_message, server_address = self.client_socket.recvfrom(BUFFER_SIZE)
    # print(modified_message.decode())
    # self.client_socket.close()
    return {}


"""
Functionality for FileServer
"""
class FileServer:
  """
  Instance variables:
  port: Port that server listens on for UDP messages from clients
  server_socket: Socket that server listens on for UDP messages from clients
  table: Registration table that stores the nick-names of all the clients,
          their status, the files that they're sharing, their IP addresses,
          and port numbers for other clients to connect to
  """
  def __init__(self, args):
    self.port = getattr(args, "port")
    self.server_socket = self.bind_server(self.port)
    self.table = dict()
    return
  
  def start_server(self, serverSocket):
    """
    """
    return
  
  def receive_info(self):
    """
    TODO: should also add the info to the registration table
    """
    welcome_message = ">>> [Welcome, You are registered.]"
    while True:
      try:
        # Receive the register message from the client.
        message, client_address = self.server_socket.recvfrom(BUFFER_SIZE)
        self.server_socket.sendto(welcome_message.encode(), client_address)
      
      # Close the server socket upon program termination
      # so it can be reused for future FileServer sessions.
      except KeyboardInterrupt:
        self.server_socket.close()
        print("Server socket closed.")
        break
    return

  def bind_server(self, serverPort):
    """
    TODO: take out functionality into separate functions
    """
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    serverSocket.bind(((''), serverPort))
    print("!!The server is ready to receive")
    return serverSocket

  def get_client_info(self):
    """
    Returns the table with the nick-names of all the clients,
    their status, the files that they're sharing, their IP addresses,
    and port numbers for other clients to connect to
    """
    pass


def main():
    """
    Handles command line args

    Format:
    FileApp -c <name> <server-ip> <server-port> <client-udp-port> <client-tcp-port>
    """
    parser = argparse.ArgumentParser(
        description="Bootleg BitTorrent File Transfer System"
    )

    # FileApp can be run in either server or client mode.
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "-s", "--server", action="store_true", help="run FileApp in server mode"
    )
    mode.add_argument(
        "-c", "--client", action="store_true", help="run FileApp in client mode"
    )
    args, unknown = parser.parse_known_args()

    # Initiate the server process via:
    #    FileApp -s <port>
    # Initiate the client communication to the server via:
    #    FileApp -c <name> <server-ip> <server-port> \
    #              <client-udp-port> <client-tcp-port>
    # Note:
    # the server process must already be running for the client to communicate.
    if args.server:
      parser.add_argument(
          "port",
          help="",
          type=int
      )
    else:
      parser.add_argument(
          "name",
          help="Client name, username for this client in this file-sharing network",
          type=str
      )
      parser.add_argument(
         "server-ip",
         type=str,
         help="Server IP address"
      )
      parser.add_argument(
          "server-port",
          help="",
          type=int
      )
      parser.add_argument(
          "client-udp-port", 
          type=int,
          help="Port that client listens on for communication with the server"
      )
      parser.add_argument(
          "client-tcp-port",
          type=int,
          help="Port that client listens for TCP connection requests from other clients for file transfers"
      )

    args = parser.parse_args()
    print("===============")
    print("Printing args:")
    for arg in vars(args):
      print(arg, getattr(args, arg))
    print("===============")
    validate_args(args, parser)

    # Run FileServer.
    if getattr(args, "server"):
      file_server = FileServer(args)
      file_server.receive_info()
      # TODO: close socket
    else:
      file_client = FileClient(args)
      file_client.register()
    return


if __name__ == "__main__":
    main()
