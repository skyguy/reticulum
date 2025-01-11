"""
This RNS example demonstrates a simple echo server.
A client can send an echo request to the server, and
the server will respond by proving receipt of the packet.
See 'echo_client.py' for the client example.
"""

import RNS

MY_NAMESPACE = "example_utilities"

reticulum = None


def main():
    global reticulum

    # Initialise Reticulum
    reticulum = RNS.Reticulum()

    # Create a new identity for our echo server
    identity = RNS.Identity()

    # We create a destination that clients can query. We want
    # to be able to verify echo replies to our clients, so we
    # create a "single" destination that can receive encrypted
    # messages. This way the client can send a request and be
    # certain that no-one else than this destination was able
    # to read it.
    destination = RNS.Destination(
        identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        MY_NAMESPACE,
        "echo"
    )

    # We configure the destination to automatically prove all
    # packets addressed to it. By doing this, RNS will automatically
    # generate a proof for each incoming packet and transmit it
    # back to the sender of that packet.
    destination.set_proof_strategy(RNS.Destination.PROVE_ALL)

    # Tell the destination which function in our program to
    # run when a packet is received. We do this so we can
    # print a log message when the server receives a request
    destination.set_packet_callback(server_callback)

    # Everything's ready!
    # Let's Wait for client requests or user input
    RNS.log(
        f"""
        Echo server running at destination: {RNS.prettyhexrep(destination.hash)}
        Copy the destination and run `echo_client.py` in a seperate terminal.
        Hit Enter to manually send an announce, Ctrl-C to quit
        """
    )

    # We enter a loop that runs until the user exits.
    # If the user hits enter, we will announce our server
    # destination on the network, which will let clients
    # know how to create messages directed towards it.
    while True:
        _ = input()
        destination.announce()
        RNS.log("Sent announce from " + RNS.prettyhexrep(destination.hash))


def server_callback(message, packet):

    # Tell the user that we received an echo request, and
    # that we are going to send a reply to the requester.
    # Sending the proof is handled automatically, since we
    # set up the destination to prove all incoming packets.
    RNS.log("Received packet from echo client, proof sent")


if __name__ == "__main__":

    main()
