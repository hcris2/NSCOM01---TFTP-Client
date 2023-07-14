
import socket
import argparse
import os
from struct import pack, unpack

DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'netascii'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}

def send_wrq(sock, server_address, filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)

def send_rrq(sock, server_address, filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)

def send_ack(sock, server_address, seq_num):
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server_address)

def send_data(sock, server_address, block_num, data):
    format = f'>hh{len(data)}s'
    data_message = pack(format, OPCODE['DATA'], block_num, data)
    sock.sendto(data_message, server_address)

# Parse command line arguments
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument("host", help="Server IP address", type=str)
parser.add_argument("action", help="get or put a file", type=str)
parser.add_argument("filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", help="Server port number", type=int, default=DEFAULT_PORT)
args = parser.parse_args()

# Create a UDP socket
server_address = (args.host, args.port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Send WRQ or RRQ message
mode = DEFAULT_TRANSFER_MODE
if args.action == "get":
    file_name = args.filename
    file_name = os.path.basename(file_name)
    print(file_name)
    send_rrq(sock, server_address, file_name, mode)
    file = open(args.filename, "wb")
    seq_number = 0
elif args.action == "put":
    file_name = args.filename
    file_name = os.path.basename(file_name)
    print(file_name)
    send_wrq(sock, server_address, file_name, mode)
    file = open(args.filename, "rb")
    seq_number = 1

try:
    while True:
        # Receive data from the server
        data, server = sock.recvfrom(516)
        opcode = int.from_bytes(data[:2], 'big')

        if opcode == OPCODE['DATA']:
            seq_number = int.from_bytes(data[2:4], 'big')
            send_ack(sock, server, seq_number)
            file_block = data[4:]
            file.write(file_block)

            if len(file_block) < BLOCK_SIZE:
                break
        elif opcode == OPCODE['ACK']:
            seq_number = int.from_bytes(data[2:4], 'big')
            file_block = file.read(BLOCK_SIZE)

            if len(file_block) == 0:
                break

            send_data(sock, server, seq_number + 1, file_block)
            if len(file_block) < BLOCK_SIZE:
                break
        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')
            print(ERROR_CODE[error_code])
            break
        else:
            break
finally:
    file.close()
    sock.close()