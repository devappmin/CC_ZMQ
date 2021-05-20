import random, threading, time, zmq, socket, argparse, json
#import matplotlib.pyplot as plt

B = 32

""" Client function """
def client(host):
    # IPv4 TCP socket that connected to bitsource
    bsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bsock.connect((host, 6750))

    # IPv4 TCP socket that connected to tally
    tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tsock.connect((host, 6704))
    
    # Input number 
    N = input("Input the number of count : ")
    tsock.sendall(str(N).encode())
    bsock.sendall(str(N).encode())


    # Get value from tally and print it
    for i in range(int(N)):
        #li = json.loads(tsock.recv(1024).decode('ascii'))
        li = tsock.recv_json()

        print('{} : {}'.format(li[0], li[1]))
        #plt.plot(li[0], li[1], 'r,')
        

    #plt.show()
    
    # Close the socket
    bsock.close()
    tsock.close()
    
""" Bitsource Function 

Also added client IP address as parameter
"""
def bitsource(zcontext, url, client):

    # Create the socket that is publisher
    # It will connected to always_yes and judge functions
    zsock = zcontext.socket(zmq.PUB)
    zsock.bind(url)
    print('zsock bind completed')
    
    # IPv4 TCP Server socket that is connected to client
    csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    csock.bind((client, 6750))
    csock.listen(1)

    # Accept client and get value 'cnt' from client
    # 'cnt' is the value 'N' in client
    sc, sockname = csock.accept()
    cnt = int(sc.recv(1024).decode("ascii"))

    # Start loop from 0 to cnt - 1
    for i in range(cnt):
        # Put 0/1 strings using ones_and_zeros function into oaz
        oaz = ones_and_zeros(B * 2)
        print('Sent {} : {}'.format(i, oaz))

        # Send oaz value to subscribers
        zsock.send_string(oaz)

        time.sleep(0.01)
    
    # Send b'DONE' to subscribers
    # It means bitsource completely sent all oaz values
    zsock.send_string(b'DONE')

    # Close TCP socket
    sc.close()

""" Ones_and_zeros function """
def ones_and_zeros(digits):
    return bin(random.getrandbits(digits)).lstrip('0b').zfill(digits)

""" Always_yes function """
def always_yes(zcontext, in_url, out_url):

    # Create the socket that is subscriber
    # It will connected to bitsource
    isock = zcontext.socket(zmq.SUB)
    isock.connect(in_url)
    
    # Filtering subscribe values to b'00' and b'DONE'
    isock.setsockopt(zmq.SUBSCRIBE, b'DONE')
    isock.setsockopt(zmq.SUBSCRIBE, b'00')

    # Create the socket that is PUSH
    # It will connected to tally
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)

    i = 0
    while True:
        # Receive string from isock(bitsource)
        recv = isock.recv_string()
        print('receive {} : {}'.format(i, recv))

        # If recv is b'DONE' not 0/1 combined string, break the loop
        if recv == b'DONE':
            print('Send done')
            break

        # Send 'Y' to PULL
        # Because (0, 0) is always true
        osock.send_string('Y')

        i += 1


""" Judge function """
def judge(zcontext, in_url, pythagoras_url, out_url):

    # Create the socket that is subscriber
    # It will connected to bitsource
    isock = zcontext.socket(zmq.SUB)
    isock.connect(in_url)

    # Filtering subscribe values to b'01', b'10', b'11' and b'DONE'
    for prefix in b'01', b'10', b'11', b'DONE':
        isock.setsockopt(zmq.SUBSCRIBE, prefix)

    # Create the socket that is request
    # It will connected to pythagoras
    psock = zcontext.socket(zmq.REQ)
    psock.connect(pythagoras_url)

    # Create the socket that is PUSH
    # It will connected to tally
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)

    # Set 2^64 value to unit
    unit = 2 ** (B * 2)
    print(unit)

    i = 0
    while True:
        # Receive string from isock(bitsource)
        bits = isock.recv_string()
        print('receive {} : {}'.format(i, bits))

        # If recv is b'DONE' not 0/1 combined string,
        # send b'DONE' to REP(pythagoras) and break the loop
        if bits == b'DONE':
            print('Send done')
            psock.send_json(b'DONE')
            break


        # Get integer value from bits string
        n, m = int(bits[::2], 2), int(bits[1::2], 2)

        # Send json (n, m) to REP(pythagoras)
        psock.send_json((n, m))
        
        # Receive value of mathmetic calculation
        sumsquares = psock.recv_json()

        # Send 'Y' or 'N' depending on sumsquares value
        osock.send_string('Y' if sumsquares < unit else 'N')

        i += 1

""" Pythagoras value """
def pythagoras(zcontext, url):

    # Create the socket that is reply
    # It will connected to judge
    zsock = zcontext.socket(zmq.REP)
    zsock.bind(url)

    while True:
        # Receive json from zsock(judge)
        numbers = zsock.recv_json()
        print('Received {}'.format(numbers))

        # If numbers is b'DONE', break the loop
        if numbers == b'DONE':
            break

        # Send json that contains [                           ] to zsock(judge)
        zsock.send_json(sum(n * n for n in numbers))
        print('Send {}'.format(sum(n * n for n in numbers)))


""" Tally function """
def tally(zcontext, url, client):
    # Create socket that is PULL
    # It will connected always_yes and judge
    zsock = zcontext.socket(zmq.PULL)
    zsock.bind(url)

    # IPv4 TCP Server socket that is connected to client
    csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    csock.bind((client, 6704))
    csock.listen(1)

    # Accept client and get value 'cnt' from client
    # 'cnt' is the value 'N' in client
    sc, sockname = csock.accept()
    cnt = int(sc.recv(1024).decode("ascii"))

    # set p = 0, q = 0
    p = q = 0

    # Start loop from 0 to cnt - 1
    for i in range(cnt):
        # Receive strings from zsock(always_yes, judge)
        decision = zsock.recv_string()

        # Add 1 to q
        q += 1

        # If decision is 'Y', add 4 to p
        if decision == 'Y':
            p += 4
        
        # Set p / q value into dvd
        dvd = p / float(q)
        print(decision, p, q, dvd)

        # Send json (q, dvd) into client
        #sc.sendall('[{}, {}]'.format(q, dvd).encode())
        sc.send_json((q, dvd))

    # Close TCP socket
    sc.close()

def main(zcontext, args):
    pubsub = 'tcp://127.0.0.1:6700'
    reqrep = 'tcp://127.0.0.1:6701'
    pushpull = 'tcp://127.0.0.1:6702'
    #start_thread(bitsource, zcontext, pubsub)
    #start_thread(always_yes, zcontext, pubsub, pushpull)
    #start_thread(judge, zcontext, pubsub, reqrep, pushpull)
    #start_thread(pythagoras, zcontext, reqrep)
    #start_thread(tally, zcontext, pushpull)
    """
    if args.b:
        start_thread(bitsource, zcontext, pubsub)
    elif args.a:
        start_thread(always_yes, zcontext, pubsub, pushpull)
    elif args.j:
        start_thread(judge, zcontext, pubsub, reqrep, pushpull)
    elif args.p:
        start_thread(pythagoras, zcontext, reqrep)
    elif args.t:
        start_thread(tally, zcontext, pushpull)
    elif args.c:
        client()
    """
    
    """
    if args.b:
        bitsource(zcontext, args.b[0], args.b[1])
    elif args.a:
        always_yes(zcontext, args.a[0], args.a[1])
    elif args.j:
        judge(zcontext, args.j[0], args.j[1], args.j[2])
    elif args.p:
        pythagoras(zcontext, args.p)
    elif args.t:
        tally(zcontext, args.t[0], args.t[1])
    elif args.c:
        client(args.c)
    """

    if args.b:
        bitsource(zcontext, pubsub, '127.0.0.1')
    elif args.a:
        always_yes(zcontext, pubsub, pushpull)
    elif args.j:
        judge(zcontext, pubsub, reqrep, pushpull)
    elif args.p:
        pythagoras(zcontext, reqrep)
    elif args.t:
        tally(zcontext, pushpull, '127.0.0.1')
    elif args.c:
        client('127.0.0.1')


    #time.sleep(30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Assignment 1 Program')
    parser.add_argument('-c', metavar='client', default=None, help='run as client')
    parser.add_argument('-b', metavar='bitsource', nargs='+', default=None, help='run as server: bitsource')
    parser.add_argument('-a', metavar='always_yes', nargs='+', default=None, help='run as server: always_yes')
    parser.add_argument('-j', metavar='judge', nargs='+', default=None, help='run as server: judge')
    parser.add_argument('-p', metavar='pythagoras', default=None, help='run as server: pythagoras')
    parser.add_argument('-t', metavar='tally', nargs='+', default=None, help='run as server: tally')
    args = parser.parse_args()

    main(zmq.Context(), args)