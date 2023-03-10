"""
Implementation of a file-sharing application using UDP and TCP sockets.

The program is run in two modes: server and client.
"""
import argparse
from socket import *
import threading

"""
GENERAL UTILITIES
"""
BUFFER_SIZE = 4096


def validate_args(args, parser):
    """
    Validates the command line arguments.
    """
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
        if port < 1024 or port > 65535:  # TODO: inclusive exclusive
            raise parser.error(
                "Port number should be an integer value in the range 1024-65535"
            )
    return


"""
Functionality for FileClient
"""


class FileClient:
    """
    FileClient listens for UDP messages from the server and TCP messages from other clients
    simultaneously using multithreading.

    It is assumed that all clients by default know the server information.

    Instance variables:
    name: Client name, username for this client in this file-sharing network
    server_ip: Server IP address
    server_port: Port that client sends UDP messages to the server
    client_udp_port: Port that client listens on for communication with the server
    client_tcp_port: Port that client listens for TCP connection requests from other clients for file transfers
    """

    def __init__(self, name, server_ip, server_port, client_udp_port, client_tcp_port):
        self.name = name
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_udp_port = client_udp_port
        self.client_tcp_port = client_tcp_port

        self.client_socket = socket(AF_INET, SOCK_DGRAM)
        self.local_table = {}
        return

    def execute_commands(self):
        while True:
            command, args = input(">>> ")
            if command == "setdir":
                self.set_dir()
            elif command == "offer":
                self.offer_file()
            elif command == "list":
                self.list_files()
            elif command == "get":
                self.get_file()
            elif command == "deregister":
                self.deregister()
            elif command == "exit":
                self.deregister()
                break
            else:
                print(">>> [Invalid command. Please try again.]")
        return

    def request_file(self, file_name, file_owner):
        """
        Sends a TCP message to the client to request the file.
        """
        print(f"< Connection with client {file_owner} established. >")
        print(f"< Downloading {file_name}... >")
        print(f"< {file_name} downloaded successfully! >")
        print(f"< Connection with client {file_owner} closed. >")

        # TODO: deny file request
        return

    def list_files(self):
        """
        Prints out the list of available file offerings by other clients.

        FileClients use only its local table to list the files that are available for download.
        """
        print(self.local_table)
        # TODO: pretty formatting?

        # If no file offerings are available:
        print(">>> [No files available for download at the moment.]")
        return

    def offer_file(self):
        """
        FileClients advertise their file offerings to other registered clients through the server.

        """
        pass

    def register(self):
        """
        Sends a UDP message to the server to register the client.
        """
        register_message = f"{self.name},{self.client_udp_port},{self.client_tcp_port}"
        self.client_socket.sendto(
            register_message.encode(), (self.server_ip, self.server_port))

        welcome_message, server_address = self.client_socket.recvfrom(BUFFER_SIZE)
        print(welcome_message.decode())
        update_message, server_address = self.client_socket.recvfrom(BUFFER_SIZE)
        print(update_message.decode())
        table, server_address = self.client_socket.recvfrom(BUFFER_SIZE)
        

        self.execute_commands()
        return

    def deregister(self):
        """
        Send a de-registration request to the server to announce that it is going offline.

        When a client is about to go offline, it immediately stops listening and ignores
        incoming requests on the TCP port for incoming file requests.
        """
        self.client_socket.close()

        print(">>> [You are now Offline. Bye.]")
        pass

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
    FileServer is used to keep track of all the clients in the network along with
    their IP addresses and the files that they are sharing. This information is
    pushed to clients and the client instances use these to communicate directly with
    each other over TCP. 

    Instance variables:
    port: Port that server listens on for UDP messages from clients
    server_socket: Socket that server listens on for UDP messages from clients
    table: Registration table that stores the nick-names of all the clients,
            their status, the files that they're sharing, their IP addresses,
            and port numbers for other clients to connect to
    """

    def __init__(self, port):
        self.port = port
        self.server_socket = self.bind_server(self.port)
        self.table = dict()
        return

    def start_server(self, serverSocket):
        """
        """
        return

    def add_client_info(self, name, status, client_ip, client_udp_port, client_tcp_port):
        """
        Adds the client information to the registration table with an empty list of files.

        It is assumed that a client will not register again using the same information after it exits via Silent leave.
        """
        self.table[name] = {
            "status": status,
            "client_ip": client_ip,
            "client_udp_port": client_udp_port,
            "client_tcp_port": client_tcp_port,
            "files": []
        }
        return

    def get_transformed_table(self):
        """
        Returns a transformed version of the table intended to be sent to clients.

        The transformed table is a dictionary of all the filenames offered by clients along with the client name of the
        file owner, the IPaddress and the TCP port number at which each file can be requested.

        This allows the registered client to initialize its local table. This transformed
        version of the table is also broadcasted whenever a client offers a new file to be shared.
        TODO: (Section 2.2)
        """
        transformed_table = dict()
        for client_info in self.table:
            pass

        return {}

    def register_client(self):
        """
        Listens for UDP messages from clients and registers them.
        """
        welcome_message = ""

        while True:
            try:
                # Receive the registration request from the client
                # Format: <name>,<client-udp-port>,<client-tcp-port>
                message, client_address = self.server_socket.recvfrom(
                    BUFFER_SIZE)
                name, client_udp_port, client_tcp_port = message.decode().split(",")

                # Check if the client is already registered.
                if name in self.table:
                    welcome_message = f"Client {name} already registered. Registration rejected."
                    self.server_socket.sendto(
                        welcome_message.encode(), client_address)
                    continue

                # Add the client information to the registration table and send a welcome message to the client.
                welcome_message = ">>> [Welcome, You are registered.]"
                self.add_client_info(
                    name, "active", client_address, client_udp_port, client_tcp_port)
                update_message = ">>> [Client table updated.]"
                self.server_socket.sendto(
                    welcome_message.encode(), client_address
                )
                self.server_socket.sendto(
                    update_message.encode(), client_address
                )

                # When a client successfully registers, the server sends the client a transformed version of the table
                transformed_table = self.get_transformed_table()
                self.server_socket.sendto(
                    str(transformed_table).encode(), client_address
                )

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
        file_server = FileServer(getattr(args, "port"))
        file_server.register_client()
    else:
        file_client = FileClient(
            getattr(args, "name"),
            getattr(args, "server-ip"),
            getattr(args, "server-port"),
            getattr(args, "client-udp-port"),
            getattr(args, "client-tcp-port")
        )
        file_client.register()
    return


if __name__ == "__main__":
    main()
