import socket
import os
from struct import pack

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

def sendRequest(sock, server_address, filename, mode, is_write):
    opcode = OPCODE['WRQ'] if is_write else OPCODE['RRQ']

    filename_bytes = bytearray(filename.encode('utf-8'))
    mode_bytes = bytearray(mode.encode('utf-8'))

    request_message = bytearray()
    request_message.append((opcode >> 8) & 0xFF)
    request_message.append(opcode & 0xFF)
    request_message += filename_bytes
    request_message.append(0)
    request_message += mode_bytes
    request_message.append(0)

    sock.sendto(request_message, server_address)


def sendAck(sock, server_address, seq_num):
    ack_message = bytearray()
    ack_message.append(0)
    ack_message.append(OPCODE['ACK'])
    ack_message.append(0)
    ack_message.append(seq_num)

    sock.sendto(ack_message, server_address)


def sendData(sock, server_address, block_num, data):
    data_message = bytearray()
    data_message.append(0)
    data_message.append(OPCODE['DATA'])
    data_message.append(0)
    data_message.append(block_num)
    data_message += data

    sock.sendto(data_message, server_address)


def main():
    print("Welcome to the TFTP Client!")

    try:
        server_ip = input("Enter the server IP address: ")
        while True:
            # Create a UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_address = (server_ip, DEFAULT_PORT)

            sock.settimeout(5)

            # Get user input
            operation = input("Enter the operation (get/put), or enter 'exit' to quit: ")
            if operation == 'exit':
                break

            completed = False  # Mark operation completion

            if operation == "get":
                filename = input("Enter the filename you want to download from the server: ")

                # Create the file path in the "downloads" folder
                file_directory = os.path.join(os.path.dirname(__file__), "downloads")
                os.makedirs(file_directory, exist_ok=True)
                file_path = os.path.join(file_directory, filename)

                # Send RRQ message
                mode = input("Enter transfer mode to be used ('netascii' or 'octet'): ")
                file_name = os.path.basename(file_path)

                try:
                    sendRequest(sock, server_address, file_name, mode, is_write=False)
                    file = open(file_path, "wb")
                    completed = True  # File upload completed successfully
                except FileNotFoundError:
                    print("\nError: No such file or directory.\n")
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

                try:
                    sendRequest(sock, server_address, server_filename, mode, is_write=True)
                    file = open(filename, "rb")
                    completed = True  # File upload completed successfully
                except FileNotFoundError:
                    print("\nError: No such file or directory.\n")
                    continue

                seq_number = 1

                print(f"Uploading {filename} to the server...")

            last_acknowledged_block = -1

            try:
                while True:
                    data, server = sock.recvfrom(516)
                    opcode = int.from_bytes(data[:2], 'big')

                    if opcode == OPCODE['DATA']:
                        seq_number = int.from_bytes(data[2:4], 'big')
                        if seq_number == last_acknowledged_block:
                            continue  # Ignore duplicate ACK
                        sendAck(sock, server, seq_number)
                        file_block = data[4:]
                        try:
                            file.write(file_block)
                        except OSError:
                            print(ERROR_CODE[3])
                            
                        if len(file_block) < BLOCK_SIZE:
                            break

                    elif opcode == OPCODE['ACK']:
                        seq_number = int.from_bytes(data[2:4], 'big')
                        if seq_number == last_acknowledged_block:
                            continue  # Ignore duplicate ACK
                        last_acknowledged_block = seq_number
                        file_block = file.read(BLOCK_SIZE)

                        if len(file_block) == 0:
                            break

                        sendData(sock, server, seq_number + 1, file_block)
                        if len(file_block) < BLOCK_SIZE:
                            break

                    elif opcode == OPCODE['ERROR']:
                        error_code = int.from_bytes(data[2:4], byteorder='big')
                        print('ERROR: ' + ERROR_CODE[error_code])
                        completed = False  # File not found, operation not completed
                        break

                    else:
                        break

            except socket.timeout:
                completed = False
                print("\nFailed to connect to the TFTP server. Please make sure the server is running and reachable.")
            finally:
                file.close()

            if completed:
                print(f"\n{operation.capitalize()} completed successfully.\n")

    except socket.gaierror:
        print("Invalid server IP address. Please try again.")

    sock.close()


if __name__ == "__main__":
    main()
