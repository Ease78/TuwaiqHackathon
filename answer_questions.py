import openai
import os
import json
import numpy as np
import textwrap
import re
from time import time,sleep
from flask import Flask, request, render_template
import config
import random

app = Flask(__name__)

openai.api_key = config.OPENAI_API_KEY

@app.route('/static/<path:filename>')
def serve_static(filename):
  return app.send_static_file(filename)

@app.route('/')
def search_form():
  return render_template('search_form.html')


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


openai.api_key = open_file('openaiapikey.txt')


def gpt3_embedding(content, engine='text-similarity-ada-001'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector


def similarity(v1, v2):  # return dot product of two vectors
    return np.dot(v1, v2)


def search_index(text, data, count=2):
    vector = gpt3_embedding(text)
    scores = list()
    for i in data:
        score = similarity(vector, i['vector'])
        #print(score)
        scores.append({'content': i['content'], 'score': score})
    ordered = sorted(scores, key=lambda d: d['score'], reverse=True)
    return ordered[0:count]


def gpt3_completion(prompt, engine='text-davinci-002', temp=0.6, top_p=1.0, tokens=2000, freq_pen=0.25, pres_pen=0.0, stop=['<<END>>']):
    max_retry = 5
    retry = 0
    prompt = prompt.encode(encoding='ASCII',errors='ignore').decode()
    while True:
        try:
            response = openai.Completion.create(
                engine=engine,
                prompt=prompt,
                temperature=temp,
                max_tokens=tokens,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                stop=stop)
            text = response['choices'][0]['text'].strip()
            #text = re.sub('\s+', ' ', text)
            filename = '%s_gpt3.txt' % time()
            with open('gpt3_logs/%s' % filename, 'w') as outfile:
                outfile.write('PROMPT:\n\n' + prompt + '\n\n==========\n\nRESPONSE:\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(1)


def openLogs():
    # list to store the parsed files
    files = []

    # Path to the folder
    path = 'gpt3_logs'

    # Retrieve the list of files in the folder
    files_in_folder = os.listdir(path)

    i=0
    # Loop through the files in the folder
    for file in files_in_folder:
        # Check for files with .txt extension
        if file.endswith('.txt'):
            # Open the file

            with open(os.path.join(path, file), 'r') as f:
                # Store the content of the file as a string in the list
                entry = f.read() #+ '<br> <img id="ad" src="static/LawDesign/'+ str(i) +'.png" alt="A description of the image">'
                files.insert(0,entry)
                i+=1
                if i == 10:
                    break;
                # print the list of strings

    return files
ads = ['<img id="ad" src="static/LawDesign/1.png" alt="A description of the image">','<img id="ad" src="static/LawDesign/2.png" alt="A description of the image">']

@app.route('/history')
def history():
    logs = openLogs()
    return render_template('search_results.html', query='history logs', results=logs, i=random.randint(1, 9))


@app.route('/search')
def search():
    with open('indexLaw.json', 'r') as infile:
        data = json.load(infile)
    #print(data)
    counter = 0
    counter2 = 0

    counter3=0
    while True:
        if counter3==1:
            break
        counter3+=1
        #query = input("Enter your question here: ")
        query = request.args.get('query')
        #print(query)
        results = search_index(query, data)
        #print(results)
        #exit(0)
        answers = list()
        # answer the same question for all returned chunks

        for result in results:
            prompt = open_file('prompt_answer.txt').replace('<<PASSAGE>>', result['content']).replace('<<QUERY>>', query)
            answer = gpt3_completion(prompt)
            print('\n\n', answer)
            answers.append(answer)
            counter+=1
            if counter == 3:
                break # exit the chunks loop
        # summarize the answers together
        all_answers = '\n\n'.join(answers)
        chunks = textwrap.wrap(all_answers, 10000)
        final = list()
        for chunk in chunks:
            prompt = open_file('prompt_summary.txt').replace('<<SUMMARY>>', chunk)
            summary = gpt3_completion(prompt)
            final.append(summary)
            counter2 += 1
            if counter2 == 1:
                break  # exit the chunks loop
        print('\n\n=========\n\n', '\n\n'.join(final))
    rand=random.randint(1, 9)

    return render_template('search_results.html', query=query, results=final, i=rand)

if __name__ == '__main__':
    app.run()
