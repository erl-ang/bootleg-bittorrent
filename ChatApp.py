"""
Implementation of a file-sharing application using UDP and TCP sockets.

The program is run in two modes: server and client.
"""
import argparse
from socket import *
import ipaddress
import os
import threading
import queue
import json
import operator
from prettytable import PrettyTable

"""
GENERAL UTILITIES
"""
# Max number of retries for the server to send its table to the client when it registers.
MAX_RETRIES = 2
BUFFER_SIZE = 4096


def validate_args(args, parser):
    """
    Validates the command line arguments.
    """
    # Server IP address should be a valid IPv4 address.
    try:
        if args.client:
            ipaddress.ip_address(getattr(args, "server-ip"))
    except ValueError:
        raise parser.error("Invalid IP address")

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

        self.client_udp_socket = socket(AF_INET, SOCK_DGRAM)
        self.client_udp_socket.bind(("", self.client_udp_port))
        self.client_tcp_socket = socket(AF_INET, SOCK_STREAM)

        # The client has to both listen to incoming server
        # updates and ACKs from the server to make sure that
        # the server has received the client's file offerings.
        # Because they are both recving from the same UDP port,
        # the thread listening for the update might get the ACK
        # or the thread listening for the ACK might get the update.
        self.work_queue = queue.Queue()

        self.local_table = dict()
        self.dir = None
        return

    def execute_commands(self):
        """
        Executes the commands entered by the client.

        Commands:
        TODO: docstring
        """
        # Initially, the client has not set a directory containing the files
        # it is going to offer.
        dir_set = False
        while True:
            try:
                command_string = input(">>> ")
                # Command will be in the form of "command arg1 arg2 ..."
                # args is [arg1, arg2, ...]
                command_args = command_string.split(" ")
                command = command_args[0]
                args = command_args[1:]

                if command == "setdir":
                    # Assumes that the directory name is the first argument.
                    # TODO: include error handling for no arguments/more than one argument.
                    dir_set = self.set_dir(args[0])
                elif command == "offer":
                    if not dir_set:
                        print(">>> [Please set a directory first. Usage: setdir <dir>.]")
                    else:
                        if len(args) == 0:
                            print(f">>> [Please provide files to offer from {self.dir}.]")
                        else:
                            self.offer_file(args)
                elif command == "list":
                    self.list_files()
                elif command == "request":
                    self.request_file(file_name=args[0], client=args[1])
                elif command == "get":
                    self.get_file()
                elif command == "deregister":
                    self.deregister()
                elif command == "exit":
                    self.deregister()
                    break
                else:
                    print(">>> [Invalid command. Please try again.]")
            except KeyboardInterrupt:
                self.client_udp_socket.close()
                print(f"!!! Client {self.name} left silently - execute_commands")
                break

        return
    
    def listen_for_server_updates(self):
        """
        The client will listen for UDP messages from the server
        on the client_udp_port.

        The UDP messages from the server can be:
        1. ACK for the client's file offerings
        2. Table update from the server
        """
        # After going through the registration process, the client's udp socket
        # is already bound to the client_udp_port. So, we don't need to bind it again.
        print(f"!!! Client {self.name} is listening for UDP messages on port {self.client_udp_port}...")
        while True:
            try:
                message, server_address = self.client_udp_socket.recvfrom(BUFFER_SIZE)
                if message.decode() == "ACK": # Message was not meant for this thread. Put it in the queue.
                    self.client_udp_socket.settimeout(None)
                    self.work_queue.put(message.decode())
                else: # The client received a broadcast table update from the server.
                    self.local_table = json.loads(message)
                print(f"!!!message: {message.decode()}")
            except Exception as e:
                print(f"!! {e}")

                self.client_udp_socket.close()
                print(f"!!! Client {self.name} left silently - listen_for_server_updates")
                break
        return
    
    def listen_for_file_requests(self):
        """
        The client will listen for TCP messages from other clients
        on the client_tcp_port.

        Note that the client acts as a server to the other clients.
        """
        self.client_tcp_socket.bind(("", self.client_tcp_port))
        self.client_tcp_socket.listen(1)
        print(f"!!! Client {self.name} is listening for TCP connections on port {self.client_tcp_port}...")

        while True:
            try:
                connection_socket, client_address = self.client_tcp_socket.accept()
                print(f"!!! Client {self.name} received a TCP connection request from {client_address}")
                # TODO: handle message
                # connection_socket.close()
            except:
                # TODO: This isn't printing for some reason.
                print(f"!!! Client {self.name} left silently - listen_for_file_requests")
                break
        return

    
    def set_dir(self, dir_name):
        """
        Section 2.2

        Sets the directory containing the files that the client is going to offer.
        """
        # Check for existence of the directory in the filesystem.
        if os.path.isdir(dir_name):
            self.dir = dir_name
            print(
                f">>> [Successfully set {dir_name} as the directory for searching offered files.]")
            return True
        else:
            print(f">>> [setdir failed: {dir_name} does not exist.]")
            return False
    
    def offer_file(self, file_list):
        """
        The offer command sends a UDP message to the server
        containing the list of files that the client is offering.

        """
        print(f"files offered: {file_list}")

        # Client must wait for an ack from the server that it has
        # successfully received the file offerings.
        # If the ack times out, the client will retry two times.
        offer_acked = False

        # The listen_for_server_updates thread will be listening for the ack.
        # but does not know how long to wait for the ack.
        self.client_udp_socket.settimeout(0.5) 
        for _ in range(MAX_RETRIES + 1): # +1 because the first try is not a retry

            # Send file offerings to the server.
            self.client_udp_socket.sendto(
                json.dumps(file_list).encode(), (self.server_ip, self.server_port)
            )
            try:
                # If there is an ack available, the listen_for_server_updates
                # thread will put the ack in the queue.
                ack = self.work_queue.get()
                if ack == "ACK":
                    print(f">>> [Offer Message received by Server.]")
                    offer_acked = True
                    break
                else:
                    continue
            except queue.Empty: # Try again.
                print("!!! Trying again")
                continue
        
        # The server's ack might never reach the client if the server
        # is too busy at the moment or if there is a network partition
        # that prevents the client message from reaching the server.
        if not offer_acked:
            print(">>> [No ACK from Server, please try again later.]")
        
        self.client_udp_socket.settimeout(None)
        return
    
    def list_files(self):
        """
        Prints out the list of available file offerings by other clients.

        FileClients use only its local table to list the files that are available for download.
        """
        # No file offerings are available.
        if len(self.local_table) == 0:
            print(">>> [No files available for download at the moment.]")
        
        # Create the formatted table using pretty table.
        formatted_table = PrettyTable(border=False, hrules=False)
        formatted_table.field_names = ["FILENAME", "OWNER", "IP ADDRESS", "TCP PORT"]
        formatted_table.align = "l"

        for file_name_owner_info in self.local_table.keys():
            file_name, owner = file_name_owner_info.split(",")
            formatted_table.add_row([
                file_name,
                owner,
                self.local_table[file_name_owner_info][0],
                self.local_table[file_name_owner_info][1]
            ])

        # Sort the table alphabetically by filename. Ties are broken by owner.
        print(formatted_table.get_string(sort_key=operator.itemgetter(0, 1), sortby="FILENAME"))
        return
        
        
    def request_file(self, args):
        """
        Sends a TCP message to the client to request the file.
        """
        print(f"< Connection with client {file_owner} established. >")
        print(f"< Downloading {file_name}... >")
        print(f"< {file_name} downloaded successfully! >")
        print(f"< Connection with client {file_owner} closed. >")

        # TODO: deny file request
        return

    def register(self):
        """
        Sends a UDP message containing the client's name, UDP port, and TCP port to the server
        in order to register itself to the server.

        Updates the client table with the information received from the server.
        """
        # Client needs to send its name and port number for file transfers
        # to the server.
        register_message = f"{self.name},{self.client_tcp_port}"
        self.client_udp_socket.sendto(
            register_message.encode(), (self.server_ip, self.server_port)
        )

        # Receive welcome message and client table from server.
        welcome_message, server_address = self.client_udp_socket.recvfrom(
            BUFFER_SIZE)
        print(welcome_message.decode())
        if welcome_message.decode() != ">>> [Welcome, You are registered.]":
            print("!!!already registered, exiting...")
            return False

        table, server_address = self.client_udp_socket.recvfrom(BUFFER_SIZE)
        # Json.loads() requires double quotes for keys and values.
        self.local_table = json.loads(table.decode())
        print(f"local table: {self.local_table}")

        # Once the table is received, the client should send an ack to the server.
        table_received_ack = ">>> [Client table updated.]"
        print(f"{table_received_ack}")
        self.client_udp_socket.sendto(
            "ACK".encode(), (self.server_ip, self.server_port) # change to server address
        )
        return True

    def deregister(self):
        """
        Send a de-registration request to the server to announce that it is going offline.

        When a client is about to go offline, it immediately stops listening and ignores
        incoming requests on the TCP port for incoming file requests.
        """
        # Notify de-registration action to the server.
        # TODO: server needs to detect and the client status should be changed to offline.
        dereg_message = "dereg {self.name}"
        self.client_udp_socket.sendto(
            dereg_message.encode(), (self.server_ip, self.server_port)
        )

        self.client_udp_socket.close()
        # TODO: close TCP socket?

        print(">>> [You are now Offline. Bye.]")
        pass

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

        self.client_table_view = dict()
        return
    
    def bind_server(self, serverPort):
        """
        TODO: take out functionality into separate functions
        """
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        serverSocket.bind(((''), serverPort))
        print("!!The server is ready to receive")
        return serverSocket

    def add_client_info(self, name, status, client_address, client_tcp_port):
        """
        Adds the client information to the registration table with an empty list of files.

        It is assumed that a client will not register again using the same information after it exits via Silent leave.
        """
        self.table[client_address] = {
            "name": name,
            "status": status,
            "client_ip": client_address[1],
            "client_tcp_port": client_tcp_port,
            "files": set()
        }
        return
    
    def add_file(self, client_address, file_name):
        """
        Adds the file to the list of files that the client is sharing to
        the registration table and the client table view.

        The same client cannot offer the same file twice.
        """
        # Add the file to the client's list of files in the server's
        # registration table.
        if file_name not in self.table[client_address]["files"]:
            self.table[client_address]["files"].add(file_name)

            # Add the file to the client table view.
            # Format:
            #   (file_name, client_name) : (client_ip, client_tcp_port)
            client_name = self.table[client_address]["name"]
            self.client_table_view[str(file_name) + "," + str(client_name)] = (
                client_address[0],
                self.table[client_address]["client_tcp_port"]
            )
        return

    # def get_transformed_table(self):
    #     """
    #     Returns a transformed version of the table intended to be sent to clients.

    #     The transformed table is a dictionary of all the filenames offered by clients along with the client name of the
    #     file owner, the IPaddress and the TCP port number at which each file can be requested.

    #     This allows the registered client to initialize its local table. This transformed
    #     version of the table is also broadcasted whenever a client offers a new file to be shared.
    #     TODO: (Section 2.2)
    #     maybe don't re-generate this every time there's an update? the methods can edit the
    #     global tranformed table directly.
    #     """
    #     # Tranformed Table Format:
    #     # {
    #     #   "filename": [{
    #     #       "ip_address": localhost,
    #     #       "tcp_port": 1234
    #     #       }, { // another client offering the same file }
    #     #   ],
    #     #   "filename2": [{ ... }, { ... }]
    #     #   }
    #     transformed_table = dict()

    #     # Format the tracker table to the transformed table to send to clients.
    #     # This format allows clients to query by a filename.
    #     for client_address, client_info in self.table.items():
    #         contact_info = {
    #             "owner": client_info,
    #             "ip_address": client_info["client_ip"],
    #             "tcp_port": client_info["client_tcp_port"]
    #         }

    #         for file in client_info["files"]:
    #             if file not in transformed_table.keys():
    #                 transformed_table[(file, ) ] = [contact_info, ]
    #             else:
    #                 transformed_table[file].append(contact_info)

    #     return transformed_table
    
    def listen_for_requests(self):
        """
        The server needs to differentiate between the following types of requests:
        1. Registration request from a client
        2. File sharing request from a client
        """
        while True:
            try:
                message, client_address = self.server_socket.recvfrom(BUFFER_SIZE)
                print(f"!!message from {client_address}: {message.decode()}")

                if client_address not in self.table.keys():
                    self.register_clients(message, client_address)
                else:
                    self.handle_client_offer(message, client_address)
            except KeyboardInterrupt: 
                # Close the server socket upon program termination
                # so it can be reused for future FileServer sessions.
                self.server_socket.close()
                print("Server terminated.")
                break
        return

    def register_clients(self, message, client_address):
        """
        Listens for UDP messages from clients and registers them.
        """
        welcome_message = ""

        # Receive the registration request from the client
        # Format: <name>, <client_udp_port>,<client_tcp_port>
        print(f"!!registration request from {client_address}: {message.decode()}")
        name, client_tcp_port = message.decode().split(",")

        # Check if the client is already registered.
        for existing_client_info in self.table.values():
            if name == existing_client_info["name"]:
                welcome_message = f"Client {name} already registered. Registration rejected."
                self.server_socket.sendto(
                    welcome_message.encode(), client_address)
                return

        # Add the client information to the registration table and send a welcome message to the client.
        welcome_message = ">>> [Welcome, You are registered.]"
        self.add_client_info(
            name, "active", client_address, int(client_tcp_port)
        )
        self.server_socket.sendto(
            welcome_message.encode(), client_address
        )

        # When a client successfully registers, the server sends the client a transformed version of the table

        # Continue if ACK received.
        # TODO: error handling
        #  - what happens when client disconnects before table is sent?
        #  - what do we resend when we retry?  welcome message and table or just table?
        # If the server does not receive an ack from the client within 500 msecs, it
        # should adopt a best effort approach by retrying 2 times.
        self.server_socket.settimeout(0.5)
        for _ in range(MAX_RETRIES + 1):  # +1 because the first try is not a retry.
            # Send the transformed table to the client.
            self.server_socket.sendto(
                str.encode(json.dumps(self.client_table_view)), client_address
            )

            try:
                ack, client_address = self.server_socket.recvfrom(
                    BUFFER_SIZE)
                if ack.decode() == "ACK":
                    break
                else:  # TODO: get rid of this
                    print("Should not be here.")
                    print(f"message received: {ack.decode()}")
            except TimeoutError:  # Try again.
                print("!!! Trying again")
                continue

        # Reset timeout to None so that it doesn't affect the next client.
        self.server_socket.settimeout(None)

        return
    
    def handle_client_offer(self, message, client_address):
        """
        Handles the file sharing request from a client. 
        The following steps are performed:
        1. The server receives the file sharing request from the client.
        2. The server's client info table will be updated with the new file information.
        3. The server will send a transformed version of the table to all the registered clients.
        To save on bandwidth, inactive clients will be ignored.


        """
        # Receive the offer from the client
        # Format: <name>, <filename>
        print(">>> [Offer Message Received By Server]")
        print(f"!!offer received: {message.decode()} from {client_address}")
        file_list = json.loads(message)
        print(f"!!file list: {file_list}")

        # Send an ACK to the client.
        self.server_socket.sendto("ACK".encode(), client_address)

        # Add the file to the client's list of files.
        # Because files is a set, duplicate file offerings
        # by the same client will be ignored.
        for file in file_list:
            self.add_file(client_address=client_address, file_name=file)
        
        # When a client offers a new file to be shared, the server sends a transformed version of the table
        # to all the registered clients. 
        # Remove inactive clients from the client table view.
        for client_file_offer in self.client_table_view:
            if self.table[client_address]["status"] != "active":
                self.client_table_view.pop(client_file_offer, "!!Already deleted") 
        
        print(f"!!current table: {self.table}")
        print(f"!!broadcasting client view: {self.client_table_view}")
                
        # Broadcast the transformed table to all the registered clients.
        for client_address in self.table.keys():
            if self.table[client_address]["status"] == "active":
                self.server_socket.sendto(
                    str.encode(json.dumps(self.client_table_view)), client_address
                )
                print(f"!!sent table to {client_address}")
        
        # Continue if ACK received.
        
        return

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
        file_server.listen_for_requests()
        
    else:
        file_client = FileClient(
            getattr(args, "name"),
            getattr(args, "server-ip"),
            getattr(args, "server-port"),
            getattr(args, "client-udp-port"),
            getattr(args, "client-tcp-port")
        )
        # If the client successfully registers with the server, execute the commands.
        if file_client.register():
            # The client needs to do three things simultaneously:
            # 1. Listen for incoming TCP connections from other clients.
            # 2. Listen for incoming UDP messages from the server.
            # 3. Listen for user input.
            # Each of these tasks is handled by a separate thread.
            # TODO: join threads when program terminates -- keyboard interrupt
            t1 = threading.Thread(target=file_client.listen_for_file_requests)
            t2 = threading.Thread(target=file_client.listen_for_server_updates)


            # Start the threads and wait for them to finish.
            # Gracefully terminate the threads when the program terminates.
            # If main thread terminates, the daemon threads will terminate.
            t1.setDaemon(True)
            t2.setDaemon(True)
            
            try:
                t1.start()
                t2.start()
                file_client.execute_commands()
            except KeyboardInterrupt:
                file_client.client_tcp_socket.close()
                file_client.client_udp_socket.close()
                t1.join()
                t2.join()

            # Close the client socket upon program termination
            # so it can be reused for future FileClient sessions.
            # file_client.client_socket.close()
            # print("Client socket closed.")
            # TODO: are these already closed in the threads?

    return


if __name__ == "__main__":
    main()
