import codecs
with codecs.open('out_brunson.txt', 'r', 'utf-16le') as f:
    lines = f.readlines()
with open('clean_debug.txt', 'w') as out_f:
    for line in lines:
        if 'DEBUG' in line:
            out_f.write(line.strip() + '\n')
