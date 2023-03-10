import argparse


def validate_args(args, parser) -> None:
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
          "server-port", help=""
      )
    else:
      parser.add_argument(
         "server-ip", help=""
      )
      parser.add_argument(
          "client-udp-port", help=""
      )
      parser.add_argument(
          "client-tcp-port", help=""
      )

    args = parser.parse_args()

    print(args)
    print("test")
    return


if __name__ == "__main__":
    main()
