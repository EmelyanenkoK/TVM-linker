# TVM linker

This module takes contract source code (both in llvm or sol 
output formats), links the code, adds standard loaders,
and packs into TON binary format. Also, it can immediately
execute it after preparation for debugging purposes.

## How to use

The linker has several modes of work:

### 1) Generating ready-to-deploy contract
    tvm_linker source-code-name --lib lib-file

Here `source-code-name` - a name of tvm asm source file, `lib-file` - a name of a library file.
Generates `address.tvc` file, where address is a hash from initial data and code of the contract.

To generate a new keypair and put the public key to the contract, call:

	tvm_linker source-code-name --lib lib-file --genkey key_file

where `key_file` - a name of the file to store public and private keys. The linker will generate 2 files: `key_file.pub` for public key and `key_file` for private key.

To load existing keypair, call:

	tvm_linker source-code-name --setkey key_file

### 2) Decoding of boc messages, prepared somewhere else.
To use this method, call

	tvm_linker source-code-name --decode

### 3) Preparing message in boc format.
The message may be either an initialization message with code,
or a message to an exisiting contract.

The command format is the same, except for --init and --data additional
agruments.

	tvm_linker source-code-name --message

If you are giving an init message, use --init option:

	tvm_linker source-code-name --message --init

If you are giving a message to an exisiting contract, use --data option:

	tvm_linker source-code-name <main-method-name> --message --data 0000

Instead of 0000 in data option, specify the necessary message body in hex
format. The code is not packed into the message, however, it is necessary
to compute address of the contract.

### 4) Emulating execution of the contract:

	tvm_linker source-code-name --lib lib-file --setkey key-file test --body XXXX... [--sign key-file] [--trace] [--decode-c6]

Generates contract and emulates contract call sending external inbound message with body defined after `--body` parameter to the contract.
If `--sign` specified, the body will be signed with the private key from `key-file` file.

Use `--trace` flag to trace VM execution, stack and registers will be printed after each executed VM command.

Use `--decode-c6` to see output actions in user friendly format.

### More Help
Use `tvm_linker --help` for detailed description about all options, flags and subcommands.

## Input format

As a temporary measure, some LLVM-assembler like input is used.
The source code should consist of functions, started by .globl keyword:

```
	.globl	x
	<code here>
```

At the end of the file a .data section may be specified.
The data from this .data section are bundled together with the code
into the init message.

```
	.globl	x
	<code here>
	.data
	00000001
```