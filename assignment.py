import random, time, zmq, argparse
import matplotlib.pyplot as plt

B = 32

""" Client function """
def client(zcontext, in_url, out_url):
    # Create the socket that is PUSH
    # and it will be connected into bitsource
    bsock = zcontext.socket(zmq.PUSH)
    bsock.connect(out_url)

    # Create the socket that is PULL
    # and it will be connected into tally
    tsock = zcontext.socket(zmq.PULL)
    tsock.connect(in_url)
    
    # Input number 
    N = input("Input the number of count : ")
    
    # Send string 'N' to bitsource socket
    bsock.send_string(str(N))

    # Loop from 0 to N - 1
    for i in range(int(N)):

        # Receive json from tally and print it
        li = tsock.recv_json()
        print(li)

        plt.plot(li[0], li[1], 'r,')
        
    plt.show()
    
""" Bitsource Function """
def bitsource(zcontext, url, client):

    # Create the socket that is publisher
    # It will be connected into always_yes and judge functions
    zsock = zcontext.socket(zmq.PUB)
    zsock.bind(url)
    print('Bind into {}'.format(url))
    
    # Create the socket that is PULL
    # It will be connected into client
    csock = zcontext.socket(zmq.PULL)
    csock.bind(client)

    # receive value 'cnt' from client
    # 'cnt' is the value 'N' in client
    cnt = int(csock.recv_string())
    print('get value: {}'.format(cnt))

    # Start loop from 0 to cnt - 1
    for i in range(cnt):
        # Put 0/1 strings using ones_and_zeros function into oaz
        oaz = ones_and_zeros(B * 2)
        print('Send {} : {}'.format(i, oaz))

        # Send oaz value to subscribers
        zsock.send_string(oaz)

        time.sleep(0.01)
    
    # Send 'DONE' to subscribers
    # It means bitsource completely sent all oaz values
    zsock.send_string('DONE')

""" Ones_and_zeros function """
def ones_and_zeros(digits):
    return bin(random.getrandbits(digits)).lstrip('0b').zfill(digits)

""" Always_yes function """
def always_yes(zcontext, in_url, out_url):

    # Create the socket that is subscriber
    # It will be connected into bitsource
    isock = zcontext.socket(zmq.SUB)
    isock.connect(in_url)
    
    # Filtering subscribe values to b'00' and b'DONE'
    isock.setsockopt(zmq.SUBSCRIBE, b'DONE')
    isock.setsockopt(zmq.SUBSCRIBE, b'00')

    # Create the socket that is PUSH
    # It will be connected into tally
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)

    i = 0
    while True:
        # Receive string from isock(bitsource)
        recv = isock.recv_string()
        print('Receive {} : {}'.format(i, recv))

        # If recv is 'DONE' not 0/1 combined string, break the loop
        if recv == 'DONE':
            osock.send_string('DONE')
            print('Close the function')
            break

        # Send 'Y' to PULL
        # Because (0, 0) is always true
        osock.send_string('Y')

        i += 1


""" Judge function """
def judge(zcontext, in_url, pythagoras_url, out_url):

    # Create the socket that is subscriber
    # It will be connected into bitsource
    isock = zcontext.socket(zmq.SUB)
    isock.connect(in_url)

    # Filtering subscribe values to b'01', b'10', b'11' and b'DONE'
    for prefix in b'01', b'10', b'11', b'DONE':
        isock.setsockopt(zmq.SUBSCRIBE, prefix)

    # Create the socket that is request
    # It will be connected into pythagoras
    psock = zcontext.socket(zmq.REQ)
    psock.connect(pythagoras_url)

    # Create the socket that is PUSH
    # It will be connected into tally
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)

    # Set 2^64 value to unit
    unit = 2 ** (B * 2)
    print(unit)

    i = 0
    while True:
        # Receive string from isock(bitsource)
        bits = isock.recv_string()
        print('Receive {} : {}'.format(i, bits))

        # If recv is 'DONE' not 0/1 combined string,
        # send 'DONE' to REP(pythagoras) and break the loop
        if bits == 'DONE':
            print('Close the function')
            psock.send_json('DONE')
            osock.send_string('DONE')
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
        print('Receive {}'.format(numbers))

        # If numbers is 'DONE', break the loop
        if numbers == 'DONE':
            break

        # Send json that contains sumsquares to zsock(judge)
        ans = sum(n * n for n in numbers)
        zsock.send_json(ans)
        print('Send {}'.format(ans))


""" Tally function """
def tally(zcontext, url, client):
    # Create the socket that is PULL
    # It will be connected into always_yes and judge
    zsock = zcontext.socket(zmq.PULL)
    zsock.bind(url)

    # Create the socket that is PUSH
    # It will be connected into client
    csock = zcontext.socket(zmq.PUSH)
    csock.bind(client)

    # set p = 0, q = 0, done_count = 0
    p = q = done_count = 0

    # Start loop until done_count became 2
    while done_count != 2:
        # Receive strings from zsock(always_yes, judge)
        decision = zsock.recv_string()

        # If we received 'DONE' bytes, add 1 to done_count
        # and continue the loop
        if decision == 'DONE':
            done_count += 1
            continue

        # Add 1 to q
        q += 1

        # If decision is 'Y', add 4 to p
        if decision == 'Y':
            p += 4
        
        # Set p / q value into dvd
        dvd = p / float(q)
        print(decision, p, q, dvd)

        # Send json (q, dvd) into client
        csock.send_json((q, dvd))

""" main function """
def main(zcontext, args):
    # Start function depending on the arguments

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
        client(zcontext, args.c[0], args.c[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Assignment 1 Program')
    parser.add_argument('-c', metavar='client', nargs='+', default=None, help='run as client')
    parser.add_argument('-b', metavar='bitsource', nargs='+', default=None, help='run as server: bitsource')
    parser.add_argument('-a', metavar='always_yes', nargs='+', default=None, help='run as server: always_yes')
    parser.add_argument('-j', metavar='judge', nargs='+', default=None, help='run as server: judge')
    parser.add_argument('-p', metavar='pythagoras', default=None, help='run as server: pythagoras')
    parser.add_argument('-t', metavar='tally', nargs='+', default=None, help='run as server: tally')
    args = parser.parse_args()

    main(zmq.Context(), args)