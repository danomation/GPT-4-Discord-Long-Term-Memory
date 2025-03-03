import os
from openai import OpenAI

client = OpenAI()
import json
import numpy as np
from numpy.linalg import norm
import re
from time import time,sleep
from uuid import uuid4
from datetime import datetime


notes_history = []


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


def timestamp_to_datetime(unix_time):
    return datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


def gpt3_embedding(message, model='text-embedding-ada-002'):
    content = message.content
    response = client.embeddings.create(input=content,model=model)
    vector = response.data[0].embedding  # this is a normal list
    return vector

def gpt3_response_embedding(response_data, model='text-embedding-ada-002'):
    content = response_data.reply_text
    response = client.embeddings.create(input=content,model=model)
    vector = response.data[0].embedding  # this is a normal list
    return vector

def gpt3_memory_embedding(content, model='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()
    response = client.embeddings.create(input=content,model=model)
    vector = response.data[0].embedding  # this is a normal list
    return vector


def similarity(v1, v2):
    # based upon https://stackoverflow.com/questions/18424228/cosine-similarity-between-2-number-lists
    return np.dot(v1, v2)/(norm(v1)*norm(v2))  # return cosine similarity


def fetch_memories(vector, logs, count):
    scores = list()
    for i in logs:
        if vector == i['vector']:
            # skip this one because it is the same message
            continue
        score = similarity(i['vector'], vector)
        i['score'] = score
        scores.append(i)
    ordered = sorted(scores, key=lambda d: d['score'], reverse=True)
    try:
        ordered = ordered[0:count]
        return ordered
    except:
        return ordered

def add_notes(notes):
    global notes_history
    notes_history.append(notes)
    return notes


def load_convo():
    files = os.listdir('./src/chat_logs')
    files = [i for i in files if '.json' in i]  # filter out any non-JSON files
    result = list()
    for file in files:
        data = load_json('./src/chat_logs/%s' % file)
        result.append(data)
    ordered = sorted(result, key=lambda d: d['timestring'], reverse=False)  # sort them all chronologically
    return ordered

def load_context():
    files = os.listdir('./src/chat_logs')
    files = [i for i in files if '.json' in i]  # filter out any non-JSON files
    result = list()
    for file in files:
        data = load_json('./src/chat_logs/%s' % file)
        result.append(data)
    ordered = sorted(result, key=lambda d: d['timestring'], reverse=False)  # sort them all chronologically
    return ordered[-2]

def load_memory():
    files = os.listdir('./src/notes')
    files = [i for i in files if '.json' in i]  # filter out any non-JSON files
    result = list()
    for file in files:
        data = load_json('./src/notes/%s' % file)
        result.append(data)
    return result

def gpt3_completion(prompt, model='gpt-3.5-turbo', temp=0.0, top_p=1.0, tokens=600, freq_pen=0.0, pres_pen=0.0, stop=['USER:', 'Jarvis:']):
    max_retry = 5
    retry = 0
    prompt = prompt.encode(encoding='ASCII',errors='ignore').decode()
    while True:
        try:
            response = client.chat.completions.create(model="gpt-4-1106-preview", #gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}])

            text = response.choices[0].message.content.strip()
            text = re.sub('[\r\n]+', '\n', text)
            text = re.sub('[\t ]+', ' ', text)
            filename = '%s_gpt3.txt' % time()
            save_file('./src/memories/%s' % filename, prompt + '\n\n==========\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(1)


def summarize_memories(memories):  # summarize a block of memories into one payload
    memories = sorted(memories, key=lambda d: d['timestamp'], reverse=False)  # sort them chronologically
    block = ''
    identifiers = list()
    timestamps = list()
    for mem in memories:
        block += mem['message'] + '\n\n'
        identifiers.append(mem['uuid'])
        timestamps.append(mem['timestamp'])
    block = block.strip()
    prompt = open_file('./src/prompt_notes.txt').replace('<<INPUT>>', block)
    notes = gpt3_completion(prompt)
    ####   SAVE NOTES
    vector = gpt3_memory_embedding(block)
    info = {'notes': notes, 'uuids': identifiers, 'times': timestamps, 'uuid': str(uuid4()), 'vector': vector}
    filename = 'notes_%s.json' % time()
    save_json('./src/notes/%s' % filename, info)
    return notes, vector
