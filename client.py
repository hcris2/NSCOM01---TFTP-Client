import socket
import os
from struct import pack, unpack

DEFAULT_PORT = 69
BLOCK_SIZE = 512

OPCODE = {
    'RRQ': 1,
    'WRQ': 2,
    'DATA': 3,
    'ACK': 4,
    'ERROR': 5
}

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


def main():
    print("Welcome to the TFTP Client!")
    while True:
        server_ip = input("Enter the server IP address: ")

        # Create a UDP socket
        server_address = (server_ip, DEFAULT_PORT)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        
        sock.settimeout(5)
        
        try:
            sock.connect(server_address)  # Check if the server is reachable
        except socket.error as e:
            print(f"Failed to connect to the TFTP server at {server_ip}:{DEFAULT_PORT}. Please make sure the server is running and reachable.")
            sock.close()
            continue
        
        while True:

            # Get user input
            operation = input("\nEnter the operation (get/put), or enter 'exit' to quit: ")
            if operation == 'exit':
                break

            if operation == "get":
                filename = input("Enter the filename you want to download from the server: ")
                print("Enter a period \".\" to save to the same directory as client.py \n", end='')
                file_directory = input("Enter the directory to save the file to: ")

                # Ensure directory path ends with a backslash
                file_directory = file_directory.rstrip("\\") + "\\"

                # Create the file path
                file_path = os.path.join(os.path.abspath(file_directory), filename)

                # Send RRQ message
                mode = input("Enter transfer mode to be used ('netascii' or 'octet'): ")
                file_name = os.path.basename(file_path)
                send_rrq(sock, server_address, file_name, mode)
                try:
                    file = open(file_path, "wb")
                except FileNotFoundError:
                    print("\nError: No such file or directory.")
                    continue
                seq_number = 0

                print(f"Downloading {filename} from the server...")

            elif operation == "put":
                print("Enter just the filename if the file is located in the same folder as your client. \n", end='')
                filename = input("Enter the directory of the file you want to upload to the server: ")
                server_filename = input("Enter the filename to be used on the server: ")

                # Send WRQ message
                mode = input("Enter transfer mode to be used ('netascii' or 'octet'): ")
                server_filename = os.path.basename(server_filename)
                send_wrq(sock, server_address, server_filename, mode)

                try:
                    print(filename)
                    file = open(filename, "rb")
                except FileNotFoundError:
                    print("Error: No such file or directory.")
                    continue

                seq_number = 1

                print(f"Uploading {filename} to the server...")

            try:
                while True:
                            

                    # Receive data from the server
                    try:
                        data, server = sock.recvfrom(516)
                        opcode = int.from_bytes(data[:2], 'big')
                    except sock.timeout:
                        print('Server is not responding! Please make sure the server is running and reachable.')
                        break

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
            except ConnectionResetError:
                print("\nFailed to connect to the TFTP server. Please make sure the server is running and reachable.")
            finally:
                file.close()

            print(f"\n{operation.capitalize()} completed successfully.")

        sock.close()


if __name__ == "__main__":
    main()
