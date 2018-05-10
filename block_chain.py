import hashlib
import json
import rsa
import uuid
from urllib.parse import urlparse
from time import time
from flask import Flask, jsonify, request


class Blockchain(object):
	def __init__(self):
		self.chain = dict()
		self.genesis_block = {
				'index': 0,
				'timestamp': 100000,
				'transactions': [],
				'proof': 100000,
				'previous_hash': 100000,
				}
		self.genesis_block['hash'] = self.get_hash(self.genesis_block)
		self.chain[self.get_hash(self.genesis_block)] = self.genesis_block
		self.nodes = set()
		self.balance = dict()
		self.balance['shop'] = 0
		self.balance['hacker'] = 10000
		self.current_transactions = []
		self.new_block(previous_hash=self.get_hash(self.genesis_block), proof=10001)
	
	def new_block(self, proof, previous_hash=None):
		if previous_hash != None:
			index = self.chain[previous_hash]['index']
			block = {
				'index': index + 1,
				'timestamp': time(),
				'transactions':self.current_transactions,
				'proof': proof,
				'previous_hash': previous_hash
				}
		else:
			block = {
				'index': int(self.last_block['index'])+1,
				'timestamp': time(),
				'transactions':self.current_transactions,
				'proof': proof,
				'previous_hash': self.get_hash(self.last_block)
				}
		self.current_transactions = []
		block['hash'] = self.get_hash(block)
		if self.valid_block(block):
			self.chain[self.get_hash(block)] = block
		return block
	
	def valid_block(self, block):
		if block['previous_hash'] in self.chain.keys():
			return True
		return False
		
	def new_transaction(self, sender, recipient, amount):
		res = self.check_balance(sender, recipient, amount)
		if res:
			self.current_transactions.append({
				'sender': sender,
				'recipient': recipient,
				'amount': amount,
			})
			return self.last_block['index'] + 1
		else:
			self.current_transactions = []
			return 0
	
	def check_balance(self, sender, recipient, amount):
		if sender in self.balance.keys() and recipient in self.balance.keys():
			if amount > self.balance[sender]:
				raise Exception("No enough coins")
			return True
		return Flase
		
	def get_balance(self, addr):
		chain = self.valid_chain(self.chain)
		self.balance['shop'] = 0
		self.balance['hacker'] = 10000
		input = 0
		output = 0
		for hash in chain.keys():
			tx = chain[hash]['transactions']
			for utxo in tx:
				if addr == utxo['sender']:
					output += utxo['amount']
				if addr == utxo['recipient']:
					input += utxo['amount']
		self.balance[addr] = self.balance[addr]+input-output
		return self.balance[addr]
			
		
	
	@staticmethod
	def get_hash(block):
		block_string = json.dumps(block, sort_keys=True).encode()
		return hashlib.sha256(block_string).hexdigest()
	
	@property
	def last_block(self):
		return max(self.chain.values(), key=lambda block: block['index'])	
		
	def proof_of_work(self, last_proof):
		proof = 0
		while self.valid_proof(last_proof, proof) is False:
			proof += 1
		return proof
	
	@staticmethod
	def valid_proof(last_proof, proof):
		guess = f'{last_proof}{proof}'.encode()
		guess_hash = hashlib.sha256(guess).hexdigest()
		return guess_hash[:4] == '0000'

	def valid_chain(self, chain):
		new_chain = {}
		new_chain[self.get_hash(self.genesis_block)] = self.genesis_block
		last_block = self.last_block
		new_chain[self.get_hash(last_block)] = last_block
		sorted_chain = sorted(chain.items(), key=lambda block:block[1]['index'], reverse=True)
		for block in sorted_chain:
			if block[0] == last_block['previous_hash']:
				new_chain[block[0]] = chain[block[0]]
				last_block = chain[block[0]]
		self.chain = new_chain
		return self.chain


app = Flask(__name__)
node_identifier = str(uuid.uuid4()).replace('-', '')
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
	prev = request.args.get('prev') if request.args.get('prev') else None
	last_block = blockchain.last_block
	last_proof = last_block['proof']
	proof = blockchain.proof_of_work(last_proof)
	if prev:
		block = blockchain.new_block(proof, prev)
	else:
		block = blockchain.new_block(proof)
	response = {
		'message': 'New Block Forged',
		'index': block['index'],
		'transactions': block['transactions'],
		'proof': block['proof'],
		'previous_hash': block['previous_hash'],
		'hash': block['hash'],
		'total_hash': blockchain.get_hash(block),
	}
	return jsonify(response), 200

@app.route('/transactions/new', methods=['GET'])
def new_transaction():
	sender = request.args.get('s')
	recipient = request.args.get('r')
	amount = int(request.args.get('a'))
	index = blockchain.new_transaction(sender, recipient,amount)
	if index > 0:
		response = {'message': f'Transaction will be added to Block {index}'}
		return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
	chain = blockchain.valid_chain(blockchain.chain)
	response = {
		'chain': chain,
		'length': len(chain),
	}
	return jsonify(response), 200

@app.route('/balance', methods=['GET'])
def get_balance():
	address = request.args.get('address')
	if address in blockchain.balance.keys():
		response = {address: blockchain.get_balance(address)}
		return jsonify(response), 200
	else:
		return jsonify({'error': 'address not found'}), 404

		
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
