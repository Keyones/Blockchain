# -*- coding: utf-8 -*-
# @File  : blockchain.py
# @Author: Keyones
# @Website: lovek.cn
# @Date  : 2018/8/7
# @Desc  :负责管理链

import hashlib
import json
import requests
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse



class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # 创建一个创世块
        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address):
        # 新增一个节点到节点集合
        # address<str> / Eg. 'http://192.168.0.6:5000'
        # 返回:None
        paesed_url = urlparse(address)
        self.nodes.add(paesed_url.netloc)
        print('新增一个节点，地址为：', address)
        print('现有所有节点：', self.nodes)


    def resolve_conflicts(self):
        # 遍历所有邻居节点，下载他们的chain，然后用valid_chain验证它
        neighbour = self.nodes
        print('当前self.nodes:', neighbour)
        new_chain = None

        # 我们只检测比我们长的链
        max_length = len(self.chain)
        print('当前链条长度：', max_length)
        # 获取和检测所有从节点获取的区块链
        for node in neighbour:
            response = requests.get(f'http://{node}/chain')
            print('response.status_code:', response.status_code)
            if response.status_code == 200:
                length = response.json()['length']
                print(f'节点{node}的链条长度：', length)
                print('response.json()[\'chain\']:', response.json()['chain'])
                chain = response.json()['chain']

            print('self.valid_chain(chain):', self.valid_chain(chain))
            # 检测长度如果是最长的则为有效链
            if length > max_length and self.valid_chain(chain):
                print('====DEBUG001=====')
                max_length = length
                new_chain = chain

        # 覆盖我们的链，如果找到一个比我们长的有效链条
        if new_chain:
            self.chain = new_chain
            return True
        else:
            return False


    def proof_of_work(self, last_proof):
        # 简单的pow工作证明算法
        # 找到一个一个数字p'，p'与前一个区块的答案p的256-hash值的后四位都是0
        # last_proof<int>:
        # 返回<int>:本区块答案
        proof =  0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        print('Proof_of_work的结果为：', proof)
        return proof

    def valid_chain(self, chain):
        # chain<list>:一个区块链
        # 返回<bool>:如果有效返回真，无效返回假

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'前一个区块：{last_block}')
            print(f'当前计算的区块：{block}')
            print('\n=====DEBUG002====\n')
            # 检查区块的hash是否正确
            if block['previous_hash'] != self.hash(last_block):
                print('hash不正确')
                return False


            # 检查工作证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                print('工作证明不正确')
                return False

            last_block = block
            current_index += 1
        return True


    @staticmethod
    def valid_proof(last_proof, proof):
        # last_proof<int>:上一个区块的答案
        # proof<int>:当前工作量证明
        # 返回<bool>:正确返回True, 错误返回False
        caculate = str(last_proof*proof)
        guess = caculate.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        if guess_hash[:4] == '0000':
            print('valid_proof计算结果为：', guess_hash)

        return guess_hash[:4] == '0000'

    def new_block(self, proof, previous_hash=None):
        # 创建一个新的区块
        # proof<int>: 工作量证明
        # previous_hash<str>: 前一个区块的hash值
        # 返回<dict>: 新的区块
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # 重置当前交易列表
        self.current_transactions = []

        self.chain.append(block)

        return block

    def new_transaction(self, sender, recipient, amount):
        # 增加一个新的交易到交易列表里
        # sender<str>: 发送者地址
        # recipient<str>: 接受地址
        # amount<int>:交易的数量
        # return<int>: 返回交易后区块索引

        self.current_transactions.append(
            {
                'sender': sender,
                'recipient': recipient,
                'amount': amount
            }
        )

        return self.last_block['index'] + 1


    @staticmethod
    def hash(block):
        # 创建一个SHA-256 的区块
        # block<dict>: 区块
        # 返回:<str>

        #确保字典是排序过的，我们才能得到正确的哈希值
        block_string = json.dumps(block, sort_keys=True).encode()
        print('block_string:', block_string)
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # 返回最后一个区块
        return self.chain[-1]


app = Flask(__name__)

# 节点的标识符
node_identifier = str(uuid4()).replace('-','')

# 实例化区块链
blockchain = Blockchain()


# 开采一个新的区块
@app.route('/mine', methods=['GET'])
def mine():
    # 执行工作量证明来开采下一个区块
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 我们接受一个奖励在寻找工作量之后
    # 发送者为'0'表示挖出一个新的区块
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )
    #
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response ={
        'message': '新的区块已经开采',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transactions():
    # 增加一个新的交易记录
    values = request.get_json()
    print('A New Transactions\' values:', values)
    # 检查请求的psot数据是否真确
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return '数据缺失', 400

    # 创建一个新的交易
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {
        'message': f'交易会被增加到区块{index}'

    }
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    # 返回整个区块链数据
    response ={
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }

    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    print('valus:', values)
    nodes = values.get('nodes')

    if nodes is None:
        return '请提供正确的节点列表', 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': '新的节点添加成功',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 200


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    print('replaced的值：', replaced)
    if replaced:
        response = {
            'message': '本地链条已经更新',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': '我们的链条为权威链条',
            'new_chain': blockchain.chain
        }
    return jsonify(response), 201


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
