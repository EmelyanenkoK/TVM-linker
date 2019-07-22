import os
import subprocess
import re
import unittest
import json
import time

'''
    TODO:
        - remove sleep(5) and just wait that account balance is changed instead
        - parse account state for data section:
                data:(just
                  value:(raw@^Cell 
                    x{}
                     x{}
                    ))
                library:hme_empty))))
        - add contract02 support
'''

cfgFile_name = __file__.replace('.py','') + '.json'
script_path = os.path.dirname(os.path.abspath(__file__))
print('Script folder {}'.format(script_path))
print('Loading config file ' + cfgFile_name)
cfgFile = None
if os.access(cfgFile_name, os.R_OK):
    with open(cfgFile_name) as cfgFile_fd:
        cfgFile = cfgFile_fd.read()
        cfgFile_fd.close()
else:
    print('Config file ' + cfgFile_name + ' not found or inaccessible for reading')
    exit(-1)
if cfgFile == None:
    print('Config file ' + cfgFile_name + ' is empty')
    exit(-2)
try:
    cfg = json.loads(cfgFile)
except json.JSONDecodeError as err:
    print('Parsing config file ' + cfgFile_name + ' error:\n' + err.msg)
    exit(-3)

def runLinker(args: str):
    cmd = cfg.get('tvm_linker').get('bin_path')
    if cfg.get('tvm_linker').get('args') != None:
        cmd = cmd + ' ' + cfg.get('tvm_linker').get('args')
    cmd = cmd + ' ' + args
    _args = cmd.split(" ")
    proc = subprocess.Popen(_args, \
        cwd = cfg.get('tvm_linker').get('work_dir', './'), \
        universal_newlines=True, \
        stdout = subprocess.PIPE, \
        stderr = subprocess.STDOUT)
    return(proc)

def runLinkerCompile(contract:str, abi_json:str = None):
    res=None
    print("Compiling {}".format(contract))
    if not(os.access(os.path.abspath(contract), os.R_OK)):
        print("Cannot access " + os.path.abspath(contract))
        return(res)
    cmd = "compile --lib " + cfg.get('tvm_linker').get('lib_path', None) + \
        " " + os.path.abspath(contract) + \
        (" --abi-json " + abi_json if abi_json!=None else "")
    # print(cmd)
    proc = runLinker(cmd)
    proc.wait()
    if proc.returncode!=0:
        err = proc.stdout.read()
        proc.stdout.close()
        print(err)
        raise Exception('Error compiling contract:')
    else:
        output = proc.stdout.read()
        proc.stdout.close()
        res = re.findall('([A-Za-z0-9]*).tvc',output)[0]
    return(res)

def runLinkerMsgInit(address:str):
    res=None
    cmd = 'message {} --init -w 0'
    proc = runLinker(cmd.format(address))
    proc.wait()
    if proc.returncode!=0:
        err = proc.stdout.read()
        proc.stdout.close()
        print(err)
        raise Exception('Error initializing message for contract')
    else:
        output = proc.stdout.read()
        proc.stdout.close()
        res = re.findall('boc file created: ([A-Za-z0-9-.]*)$',output)[0]
    return(res)

def runLinkerMsgBody(address:str, abi_json:str, abi_params:str, method:str):
    res=None
    if not(os.access(os.path.abspath(abi_json), os.R_OK)):
        return(res)
    cmd = 'message {} -w 0 --abi-json {} --abi-method {} --abi-params {}'
    cmd = cmd.format(address, os.path.abspath(abi_json), method, abi_params)
    # print(cmd)
    proc = runLinker(cmd)
    proc.wait()
    if proc.returncode!=0:
        err = proc.stdout.read()
        proc.stdout.close()
        print(err)
        raise Exception('Error preparing message body for contract')
    else:
        output = proc.stdout.read()
        # print(output)
        proc.stdout.close()
        res = re.findall(r'boc file created: ([A-Za-z0-9-\.]*)$',output)[0]
    return(res)

def runSDK(args:str):
    cmd = cfg.get('sdk').get('bin_path')
    if cfg.get('sdk').get('args') != None:
        cmd = cmd + ' ' + cfg.get('sdk').get('args')
    cmd = cmd + ' ' + args
    _args = cmd.split(" ")
    proc = subprocess.Popen(_args, \
        cwd = cfg.get('sdk').get('work_dir', './'), \
        universal_newlines=True, \
        stdout = subprocess.PIPE, \
        stderr = subprocess.STDOUT)
    return(proc)

def runCreateMessage(src:str, dst:str, amount:str, out_file:str):
    res=None
    cmd = '--type transfer --src {} --dst {} --value {} --out {}'
    proc = runSDK(cmd.format(src, dst, amount, os.path.abspath(out_file)))
    proc.wait()
    if proc.returncode!=0:
        err = proc.stdout.read()
        proc.stdout.close()
        print(err)
        raise Exception('Error compiling contract:')
    else:
        output = proc.stdout.read()
        proc.stdout.close()
        res = re.findall(r'BoC succsessfully saved: ([A-Za-z0-9/\-_]*.boc)$',output)[0]
    return(res)

def runTLC(args:str):
    cmd = cfg.get('tlc').get('bin_path')
    if cfg.get('tlc').get('args') != None:
        cmd = cmd + ' ' + cfg.get('tlc').get('args')
    if args!=None:
        cmd = cmd + ' ' + args
    _args = cmd.split(" ")
    proc = subprocess.Popen(_args, \
        cwd = cfg.get('tlc').get('work_dir', './'), \
        universal_newlines=True, \
        stdout = subprocess.PIPE, \
        stderr = subprocess.STDOUT)
    return(proc)

lastLine = None

def runTLCAccount(address:str):
    global lastLine
    print("Getting account " + address)
    res = None
    cmd = '-a 0:{}'
    proc = runTLC(cmd.format(address))
    st = time.time()*1000
    ec = proc.poll()
    while (ec == None) and (time.time()*1000-st) < 3000:
        ec = proc.poll()
        time.sleep(0.1)
    if ec == None:
        print("timeout")
        # print(proc.pid)
        proc.terminate()
        return ""
    res = proc.stdout.read()

    # print last line of output where data section is
    lastLine = res.splitlines()[-1]
    
    # print account balance
    regex = re.compile(r"grams:\(nanograms.*?\)\)", re.MULTILINE | re.DOTALL)
    match = regex.search(res)
    if match: print(match.group(0).replace("\n", " "))
    
    proc.stdout.close()
    return res

def runTLCFile(boc_file:str):
    res=None
    if not(os.access(os.path.abspath(boc_file), os.R_OK)):
        return(res)
    cmd = '-f {}'
    proc = runTLC(cmd.format(boc_file))
    st = time.time()*1000
    ec = proc.poll()
    while ec==None and (time.time()*1000-st)<10000:
        ec = proc.poll()
        time.sleep(0.1)
    if ec==None:
        proc.terminate()
    res = proc.stdout.read()
    proc.stdout.close()
    return(res)

def waitFor(function, args, timeout, condition):
    sdt = int(round(time.time()*1000))
    res = {'result': False, 'output': None}
    while (res['output']==None or len(re.findall(condition, res['output']))<1) and (int(round(time.time()*1000))-sdt)<timeout:
        res['output'] = function(*args)
        time.sleep(0.25)
    if len(re.findall(condition, res['output']))==0:
        print('Looking for:\n{}\nOutput:\n{}'.format(condition, res['output']))
        raise Exception('Unable to find condition string in output')
    else:
        res['result'] = True
    return(res)        

class SoliditySuite(unittest.TestCase):
    def setUp(self):
        self.cfg = cfg
        self.assertNotEqual(self.cfg.get('node', None), None, 'No node config provided')
        wd = self.cfg['node'].get('work_dir',None)
        if wd != None: 
            self.assertTrue(os.access(wd, os.R_OK), 'No node workdir found')
            os.chdir(wd)
        subprocess.call('pkill ton-node', shell=True)
        subprocess.call('rm -f ./log/output.log', shell=True)
        subprocess.call('rm -rf ./workchains', shell=True)
        cmd = self.cfg['node'].get('cmd')
        self.node = None
        self.node = subprocess.Popen(cmd, shell=True)
        
        # give some time for node to start
        time.sleep(1)
        
        os.chdir(script_path)
        subprocess.call('rm -f *.tvc *.boc *.tmp', shell=True)
        
    def tearDown(self):
        if self.node!=None:
            self.node.terminate()
            self.node.wait()
        subprocess.call('pkill ton-node', shell=True)
        
    def deployContract(self, contractName):
        address = runLinkerCompile('contract01.code', 'contract01.abi.json')
        print('Contract address:', address)
        self.assertNotEqual(address,None, 'Contract hasn\'t been compiled')
        msginit = runLinkerMsgInit(address)
        self.assertNotEqual(msginit, None, 'No msg init boc file created')
        print('Message init file:', msginit)
        
        msgfile = runCreateMessage('0000000000000000000000000000000000000000000000000000000000000000', address, '1000000', './sendmoney.boc')
        self.assertEqual(msgfile, os.path.abspath('./sendmoney.boc'), 'Expected message file wasn\'t been created')
        print('Created message file:', msgfile)
        print('')

        # fetching state of zero account to make sure node is up
        waitFor(runTLCAccount, ["0" * 64], 5000, r'state:\(account_active')

        waitFor(runTLCFile, [msgfile], 5000, r'external message status is 1')
        waitFor(runTLCAccount, [address], 5000, r'state:account_uninit')
        
        waitFor(runTLCFile, [msginit], 5000, r'external message status is 1')
        waitFor(runTLCAccount, [address], 5000, r'state:\(account_active')
        
        return address
    
    
    def test_01(self):
        address = self.deployContract("contract01")
    
        msgbody = runLinkerMsgBody(address, 'contract01.abi.json', '{"a":"0x1234"}', 'main_external')
        self.assertNotEqual(msgbody, None, 'No msg body boc file created')
        print('Message body file:', msgbody)

        waitFor(runTLCAccount, [address], 5000, r'state:\(account_active')
        print(lastLine)
        self.assertEqual(lastLine, " x{4_}")

        waitFor(runTLCFile, [msgbody], 5000, r'external message status is 1')

        # TODO: this sleep() should be avoided!
        time.sleep(5)

        waitFor(runTLCAccount,[address], 5000, r'state:\(account_active')
        print(lastLine)
        self.assertEqual(lastLine, "  x{D000000000000000000000000000000000000000000000000000000000000001234}")
        
if __name__ == '__main__':
    unittest.main()