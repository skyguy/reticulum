#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2023 Mark Qvist / unsigned.io
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import RNS
import argparse
import time
import sys
import os

from RNS._version import __version__

APP_NAME = "rnid"

SIG_EXT = "rsg"
ENCRYPT_EXT = "rfe"
CHUNK_SIZE = 16*1024*1024

def spin(until=None, msg=None, timeout=None):
    i = 0
    syms = "⢄⢂⢁⡁⡈⡐⡠"
    if timeout != None:
        timeout = time.time()+timeout

    print(msg+"  ", end=" ")
    while (timeout == None or time.time()<timeout) and not until():
        time.sleep(0.1)
        print(("\b\b"+syms[i]+" "), end="")
        sys.stdout.flush()
        i = (i+1)%len(syms)

    print("\r"+" "*len(msg)+"  \r", end="")

    if timeout != None and time.time() > timeout:
        return False
    else:
        return True

def main():
    try:
        parser = argparse.ArgumentParser(description="Reticulum Identity & Encryption Utility")
        # parser.add_argument("file", nargs="?", default=None, help="input file path", type=str)

        parser.add_argument("--config", metavar="path", action="store", default=None, help="path to alternative Reticulum config directory", type=str)
        parser.add_argument("-i", metavar="identity", action="store", default=None, help="hexadecimal Reticulum Destination hash or path to Identity file", type=str)
        parser.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
        parser.add_argument("-q", "--quiet", action="count", default=0, help="decrease verbosity")

        parser.add_argument("-e", "--encrypt", action="store_true", default=False, help="encrypt data")
        parser.add_argument("-d", "--decrypt", action="store_true", default=None, help="decrypt data")
        parser.add_argument("-s", "--sign", action="store_true", default=None, help="sign data")
        parser.add_argument("-V", "--verify", action="store_true", default=None, help="verify signature")

        parser.add_argument("-r", "--read", metavar="path", action="store", default=None, help="input file path", type=str)
        parser.add_argument("-w", "--write", metavar="path", action="store", default=None, help="output file path", type=str)
        parser.add_argument("-f", "--force", action="store_true", default=None, help="write output even if it overwrites existing files")
        parser.add_argument("-I", "--stdin", action="store_true", default=False, help=argparse.SUPPRESS) # "read input from STDIN instead of file"
        parser.add_argument("-O", "--stdout", action="store_true", default=False, help=argparse.SUPPRESS) # help="write output to STDOUT instead of file", 

        parser.add_argument("-R", "--request", action="store_true", default=False, help="request unknown Identities from the network")
        parser.add_argument("-t", action="store", metavar="seconds", type=float, help="identity request timeout before giving up", default=RNS.Transport.PATH_REQUEST_TIMEOUT)
        parser.add_argument("-p", "--print-identity", action="store_true", default=False, help="print identity info and exit")
        parser.add_argument("-P", "--print-private", action="store_true", default=False, help="allow displaying private keys")

        parser.add_argument("-b", "--base64", action="store_true", default=False, help="Use base64-encoded input and output")

        parser.add_argument("--version", action="version", version="rncp {version}".format(version=__version__))
        
        args = parser.parse_args()

        ops = 0;
        for t in [args.encrypt, args.decrypt, args.verify, args.sign]:
            if t:
                ops += 1
        
        if ops > 1:
            RNS.log("This utility currently only supports one of the encrypt, decrypt, sign or verify operations per invocation", RNS.LOG_ERROR)
            exit(1)

        identity_str = args.i
        if not identity_str:
            print("\nNo identity provided, cannot continue\n")
            parser.print_help()
            print("")
            sys.exit(1)

        else:
            targetloglevel = 4
            verbosity = args.verbose
            quietness = args.quiet
            if verbosity != 0 or quietness != 0:
                targetloglevel = targetloglevel+verbosity-quietness
            
            # Start Reticulum
            reticulum = RNS.Reticulum(configdir=args.config, loglevel=targetloglevel)
            RNS.compact_log_fmt = True
            if args.stdout:
                RNS.loglevel = -1

            identity = None
            if len(identity_str) == RNS.Reticulum.TRUNCATED_HASHLENGTH//8*2 and not os.path.isfile(identity_str):
                # Try recalling Identity from hex-encoded hash
                try:
                    destination_hash = bytes.fromhex(identity_str)
                    identity = RNS.Identity.recall(destination_hash)

                    if identity == None:
                        if not args.request:
                            RNS.log("Could not recall Identity for "+RNS.prettyhexrep(destination_hash)+".", RNS.LOG_ERROR)
                            RNS.log("You can query the network for unknown Identities with the -R option.", RNS.LOG_ERROR)
                            exit(2)
                        else:
                            RNS.Transport.request_path(destination_hash)
                            def spincheck():
                                return RNS.Identity.recall(destination_hash) != None
                            spin(spincheck, "Requesting unknown Identity for "+RNS.prettyhexrep(destination_hash), args.t)

                            if not spincheck():
                                RNS.log("Identity request timed out", RNS.LOG_ERROR)
                                exit(3)
                            else:
                                RNS.log("Received Identity "+str(identity)+" for destination "+RNS.prettyhexrep(destination_hash)+" from the network")
                                identity = RNS.Identity.recall(destination_hash)

                    else:
                        RNS.log("Recalled Identity "+str(identity)+" for destination "+RNS.prettyhexrep(destination_hash))


                except Exception as e:
                    RNS.log("Invalid hexadecimal hash provided", RNS.LOG_ERROR)
                    exit(4)

                
            else:
                # Try loading Identity from file
                if not os.path.isfile(identity_str):
                    RNS.log("Specified Identity file not found")
                    exit(5)
                else:
                    try:
                        identity = RNS.Identity.from_file(identity_str)
                        RNS.log("Loaded Identity "+str(identity)+" from "+str(identity_str))

                    except Exception as e:
                        RNS.log("Could not decode Identity from specified file")
                        exit(6)

            if identity != None:
                if args.print_identity:
                    RNS.log("Public Key  : "+RNS.hexrep(identity.pub_bytes, delimit=False))
                    if identity.prv:
                        if args.print_private:
                            RNS.log("Private Key : "+RNS.hexrep(identity.prv_bytes, delimit=False))
                        else:
                            RNS.log("Private Key : Hidden")
                    exit(0)

                data_input = None
                if args.read:
                    if not os.path.isfile(args.read):
                        RNS.log("Input file "+str(args.read)+" not found", RNS.LOG_ERROR)
                        exit(7)
                    else:
                        try:
                            data_input = open(args.read, "rb")
                        except Exception as e:
                            RNS.log("Could not open input file for reading", RNS.LOG_ERROR)
                            RNS.log("The contained exception was: "+str(e), RNS.LOG_ERROR)
                            exit(8)

                # TODO: Actually expand this to a good solution
                # probably need to create a wrapper that takes
                # into account not closing stdin when done
                # elif args.stdin:
                #     data_input = sys.stdin

                data_output = None
                if args.encrypt and not args.write and not args.stdout and args.read:
                    args.write = str(args.read)+"."+ENCRYPT_EXT

                if args.decrypt and not args.write and not args.stdout and args.read and args.read.lower().endswith("."+ENCRYPT_EXT):
                    args.write = str(args.read).replace("."+ENCRYPT_EXT, "")

                if args.write:
                    if not args.force and os.path.isfile(args.write):
                        RNS.log("Output file "+str(args.write)+" already exists. Not overwriting.", RNS.LOG_ERROR)
                        exit(9)
                    else:
                        try:
                            data_output = open(args.write, "wb")
                        except Exception as e:
                            RNS.log("Could not open output file for writing", RNS.LOG_ERROR)
                            RNS.log("The contained exception was: "+str(e), RNS.LOG_ERROR)
                            exit(9)
                
                # TODO: Actually expand this to a good solution
                # probably need to create a wrapper that takes
                # into account not closing stdout when done
                # elif args.stdout:
                #     data_output = sys.stdout

                if args.encrypt:
                    if not data_input:
                        if not args.stdout:
                            RNS.log("Encryption requested, but no input data specified", RNS.LOG_ERROR)
                        exit(10)
                    else:
                        if not data_output:
                            if not args.stdout:
                                RNS.log("Encryption requested, but no output specified", RNS.LOG_ERROR)
                            exit(11)

                        if not args.stdout:
                            RNS.log("Encrypting "+str(args.read))
                        
                        try:
                            more_data = True
                            while more_data:
                                chunk = data_input.read(CHUNK_SIZE)
                                if chunk:
                                    data_output.write(identity.encrypt(chunk))
                                else:
                                    more_data = False
                            data_output.close()
                            data_input.close()
                            if not args.stdout:
                                if args.read:
                                    RNS.log("File "+str(args.read)+" encrypted for "+str(identity)+" to "+str(args.write))
                                    exit(0)

                        except Exception as e:
                            if not args.stdout:
                                RNS.log("An error ocurred while encrypting data.", RNS.LOG_ERROR)
                                RNS.log("The contained exception was: "+str(e), RNS.LOG_ERROR)
                            try:
                                data_output.close()
                            except:
                                pass
                            try:
                                data_input.close()
                            except:
                                pass
                            exit(12)

                if args.decrypt:
                    if identity.prv == None:
                        RNS.log("Specified Identity does not hold a private key. Cannot decrypt.", RNS.LOG_ERROR)
                        exit(13)

                    if not data_input:
                        if not args.stdout:
                            RNS.log("Decryption requested, but no input data specified", RNS.LOG_ERROR)
                        exit(10)
                    else:
                        if not data_output:
                            if not args.stdout:
                                RNS.log("Decryption requested, but no output specified", RNS.LOG_ERROR)
                            exit(11)

                        if not args.stdout:
                            RNS.log("Decrypting "+str(args.read)+"...")
                        
                        try:
                            more_data = True
                            while more_data:
                                chunk = data_input.read(CHUNK_SIZE)
                                if chunk:
                                    plaintext = identity.decrypt(chunk)
                                    if plaintext == None:
                                        if not args.stdout:
                                            RNS.log("Data could not be decrypted with the specified Identity")
                                        exit(14)
                                    else:
                                        data_output.write(plaintext)
                                else:
                                    more_data = False
                            data_output.close()
                            data_input.close()
                            if not args.stdout:
                                if args.read:
                                    RNS.log("File "+str(args.read)+" decrypted with "+str(identity)+" to "+str(args.write))
                                    exit(0)

                        except Exception as e:
                            if not args.stdout:
                                RNS.log("An error ocurred while decrypting data.", RNS.LOG_ERROR)
                                RNS.log("The contained exception was: "+str(e), RNS.LOG_ERROR)
                            try:
                                data_output.close()
                            except:
                                pass
                            try:
                                data_input.close()
                            except:
                                pass
                            exit(12)

            if True:
                pass

            elif False:
                pass

            else:
                print("")
                parser.print_help()
                print("")

    except KeyboardInterrupt:
        print("")
        exit()

if __name__ == "__main__":
    main()