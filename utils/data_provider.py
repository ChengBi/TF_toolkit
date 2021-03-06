import numpy as np
import pickle
# from cmd_io import *
from logging_io import *
import cv2
import os

class dataProvider(object):

    def __init__(self):
        raise NotImplementedError

    def n_batches(self):
        raise NotImplementedError

    def n_samples(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def _new_epoch(self):
        raise NotImplementedError

    def shuffle(self):
        raise NotImplementedError

    def __iter__(self):
        return self

    def next():
        return __next__(self)

    def __next__(self):
        raise NotImplementedError

    def one_hot(self):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError


class MNISTProvider(dataProvider):

    def __init__(self, filename, batch_size, isShuffle = True, isOneHot = False, isAutoEncoder = False):
        self.inputs = np.load(open(filename, 'rb'))['inputs']
        self.targets = np.load(open(filename, 'rb'))['targets']
        self._filename = filename
        self._current_index = 0
        self._batch_size = batch_size
        self._n_samples = len(self.targets)
        self.isShuffle = isShuffle
        self.isOneHot = isOneHot
        self.isAutoEncoder = isAutoEncoder
        self._current_order = np.arange(self._n_samples)
        if self._n_samples % self._batch_size == 0:
            self._n_batches = int(self._n_samples/self._batch_size)
        else:
            self._n_batches = int(self._n_samples/self._batch_size)+1
        if self.isOneHot == False:
            self.one_hot()
        else:
            self._n_classes = len(self.targets[0])
        if self.isShuffle == True:
            self.shuffle()

    def n_batches(self):
        return self._n_batches

    def n_samples(self):
        return self._n_samples

    def reset(self):
        self._current_order = np.arange(self._n_samples)
        self._new_epoch()
        print('reset')

    def _new_epoch(self):
        self._current_index = 0
        if self.isShuffle == True:
            self.shuffle()
        # print('new_epoch')

    def shuffle(self):
        np.random.shuffle(self._current_order)

    def __iter__(self):
        return self

    def next():
        return __next__(self)

    def __next__(self):
        if self._current_index >= self._n_batches:
            self._new_epoch()
            raise StopIteration
        else:
            slide_index = self._current_order[self._current_index*self._batch_size:(self._current_index+1)*self._batch_size]
            batch_inputs = self.inputs[slide_index]
            batch_targets = self.targets[slide_index]
            self._current_index += 1
            if self.isAutoEncoder:
                return batch_inputs, batch_inputs
            return batch_inputs, batch_targets

    def one_hot(self):
        self._n_classes = len(list(set(self.targets)))
        one_hot_res = np.zeros((self._n_samples, self._n_classes))
        for target, i in zip(self.targets, range(self._n_samples)):
            one_hot_res[i][int(target)] = 1.0
        self.targets = one_hot_res

    def __str__(self):
        return logging_io.BUILD('\n{0:40}\n|{1:^38}|\n{0:40}\n'+
                                '| {2:17}| {3:17} |\n'+
                                '| {4:17}| {5:17} |\n'+
                                '| {6:17}| {7:17} |\n'+
                                '| {8:17}| {9:17} |\n'+
                                '| {10:17}| {11:17} |\n'+
                                '{0:40}\n'
                                ).format('+'+'-'*38+'+',
                                        'MNIST DATA PROVIDER',
                                        'n_samples',
                                        self._n_samples,
                                        'n_batch',
                                        self._n_batches,
                                        'batch_size',
                                        self._batch_size,
                                        'shuffle',
                                        self.isShuffle,
                                        'one_hot',
                                        self.isOneHot)


class idProvider():

    def __init__(self, filename, batch_size):
        self.filename = filename
        self.batch_size = batch_size
        self._currentPosition = 0
        self.loadCorpus()
        # for key in self.batched_inputs.keys():
        #     print(key, len(self.batched_inputs[key]))

    def reset(self):
        self._currentOrder = self.keys.copy()
        self.new_epoch()

    def new_epoch(self):
        np.random.shuffle(self._currentOrder)
        self._currentPosition = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._currentPosition >= self.n_batches:
            self.new_epoch()
            raise StopIteration
        batch_input = self.batched_inputs[self._currentOrder[self._currentPosition]]
        batch_target = self.batched_targets[self._currentOrder[self._currentPosition]]
        length = int(self._currentOrder[self._currentPosition].split('_')[0])
        # print(self._currentOrder[self._currentPosition])
        self._currentPosition += 1
        return length, batch_input, batch_target

    def next(self):
        return self.__next__()

    def loadCorpus(self):
        lines = open(self.filename).readlines()
        varLen_inputs = dict()
        varLen_targets = dict()
        for line in lines:
            splited = line.split()
            ids = [int(i) for i in splited[1:]]
            targets = int(splited[0])
            key = len(ids)
            if key not in varLen_inputs.keys():
                varLen_inputs[key] = []
                varLen_targets[key] = []
            varLen_inputs[key].append(ids)
            varLen_targets[key].append(targets)
        self.batched_inputs = dict()
        self.batched_targets = dict()
        for key in varLen_targets.keys():
            if len(varLen_targets[key])%self.batch_size == 0:
                count = int(len(varLen_targets[key])/self.batch_size)
            else:
                count = int(len(varLen_targets[key])/self.batch_size) + 1
            for i in range(count):
                new_key = str(key) + '_' + str(i)
                if i == count - 1:
                    self.batched_inputs[new_key] = varLen_inputs[key][i*self.batch_size:]
                    self.batched_targets[new_key] = varLen_targets[key][i*self.batch_size:]
                else:
                    self.batched_inputs[new_key] = varLen_inputs[key][i*self.batch_size:(i+1)*self.batch_size]
                    self.batched_targets[new_key] = varLen_targets[key][i*self.batch_size:(i+1)*self.batch_size]

        self.keys = list(self.batched_targets.keys())
        self.n_batches = len(self.keys)
        self.reset()


class KerasSeq2SeqDataProvider():

    def __init__(self, filename, batch_size, label_map_dir, dictionary_dir, max_word, remainIds = False):
        self.filename = filename
        self.batch_size = batch_size
        self._currentPosition = 0
        self.label_map_dir = label_map_dir
        self.dictionary_dir = dictionary_dir
        self.max_word = max_word
        self.remainIds = remainIds
        self.loadCorpus()

    def reset(self):
        self._currentOrder = np.arange(self._n_samples)
        self.new_epoch()

    def new_epoch(self):
        np.random.shuffle(self._currentOrder)
        self._currentPosition = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._currentPosition >= self._n_batches:
            self.new_epoch()
            raise StopIteration
        if self._currentPosition == self._n_batches - 1:
            batch_input = self.vocIndex2vector(self.corpus['inputs'][self._currentPosition*self.batch_size:])
            batch_target = self.tagIndex2vector(self.corpus['targets'][self._currentPosition*self.batch_size:])
        else:
            batch_input = self.vocIndex2vector(self.corpus['inputs'][self._currentPosition*self.batch_size:(self._currentPosition+1)*self.batch_size])
            batch_target = self.tagIndex2vector(self.corpus['targets'][self._currentPosition*self.batch_size:(self._currentPosition+1)*self.batch_size])
        self._currentPosition += 1
        logging_io.DEBUG_INFO(batch_input.shape)
        logging_io.DEBUG_INFO(batch_target.shape)
        return batch_input, batch_target

    def next(self):
        return self.__next__()

    def loadCorpus(self):
        self.label_map = pickle.load(open(self.label_map_dir, 'rb'))
        self.dictionary = pickle.load(open(self.dictionary_dir, 'rb'))
        lines = open(self.filename).readlines()
        self._n_samples = len(lines)
        self._n_voc_size = len(self.dictionary)
        self._n_classes = len(self.label_map)
        self.corpus = dict()
        self.corpus['inputs'] = [None]*self._n_samples
        self.corpus['targets'] = [None]*self._n_samples
        for line, index in zip(lines, range(self._n_samples)):
            splited = [int(i) for i in line.split()]
            tag = splited[0]
            words = splited[1:]
            if len(words) > self.max_word:
                words = words[:self.max_word]
            self.corpus['inputs'][index] = words
            self.corpus['targets'][index] = tag
        if self._n_samples % self.batch_size == 0:
            self._n_batches = int(self._n_samples / self.batch_size)
        else:
            self._n_batches = int(self._n_samples / self.batch_size) + 1
        self.reset()

    def vocIndex2vector(self, ids):
        n_sentence = len(ids)
        results = [None]*n_sentence
        if self.remainIds == False:
            for i in range(n_sentence):
                n_words = len(ids[i])
                temp = np.zeros((self.max_word, self._n_voc_size))
                for j in range(n_words):
                    temp[j, ids[i][j]] = 1.0
                if n_words < self.max_word:
                    for j in range(n_words, self.max_word):
                        temp[j, self.dictionary.index('<END>')] = 1.0
                results[i] = temp
        else:
            results = np.zeros((n_sentence, self.max_word)) + self.dictionary.index('<END>')
            for i in range(n_sentence):
                n_words = len(ids[i])
                results[i, :n_words] = ids[i]
        return np.array(results)

    def tagIndex2vector(self, tags):
        results = np.zeros((len(tags), self._n_classes))
        for i in range(len(tags)):
            results[i][tags[i]] = 1.0
        return np.array(results)


class CIFARProvider(object):

    def __init__(self, filename, batch_size, isShuffle = True, isOneHot = False, isAutoEncoder = False):

        try:
            data = pickle.load(open(filename, 'rb'))
        except:
            data = np.load(filename)
        tags = data.keys()
        self.inputs = data['inputs']#[:5000]

        if "targets" in tags:
            self._train_mode = True
            self.targets = data['targets']#[:5000]
            self._label_map = data['label_map']
        else:
            self._train_mode = False

        self._filename = filename
        self._current_index = 0
        self._batch_size = batch_size
        self._n_samples = len(self.targets)
        self.isShuffle = isShuffle
        self.isOneHot = isOneHot
        self.isAutoEncoder = isAutoEncoder
        self._current_order = np.arange(self._n_samples)

        if self._train_mode:
            if self._n_samples % self._batch_size == 0:
                self._n_batches = int(self._n_samples/self._batch_size)
            else:
                self._n_batches = int(self._n_samples/self._batch_size)+1
            self._n_classes = len(self._label_map)
            if self.isOneHot == False:
                self.one_hot()

        if self.isShuffle == True:
            self.shuffle()

    def n_batches(self):
        return self._n_batches

    def n_samples(self):
        return self._n_samples

    def reset(self):
        self._current_order = np.arange(self._n_samples)
        self._new_epoch()
        print('reset')

    def _new_epoch(self):
        self._current_index = 0
        if self.isShuffle == True:
            self.shuffle()
        # print('new_epoch')

    def shuffle(self):
        np.random.shuffle(self._current_order)

    def __iter__(self):
        return self

    def next():
        return __next__(self)

    def __next__(self):
        if self._current_index >= self._n_batches:
            self._new_epoch()
            raise StopIteration
        else:
            slide_index = self._current_order[self._current_index*self._batch_size:(self._current_index+1)*self._batch_size]
            batch_inputs = self.inputs[slide_index]
            batch_targets = self.targets[slide_index]
            self._current_index += 1
            batch_inputs = batch_inputs.reshape([-1, 3, 32, 32]).transpose([0, 2, 3, 1])
            if self.isAutoEncoder:
                return batch_inputs, batch_inputs
            return batch_inputs, batch_targets

    def one_hot(self):
        one_hot_res = np.zeros((self._n_samples, self._n_classes))
        for target, i in zip(self.targets, range(self._n_samples)):
            one_hot_res[i][int(target)] = 1.0
        self.targets = one_hot_res

    def __str__(self):
        return logging_io.BUILD('\n{0:40}\n|{1:^38}|\n{0:40}\n'+
                                '| {2:17}| {3:17} |\n'+
                                '| {4:17}| {5:17} |\n'+
                                '| {6:17}| {7:17} |\n'+
                                '| {8:17}| {9:17} |\n'+
                                '| {10:17}| {11:17} |\n'+
                                '{0:40}\n'
                                ).format('+'+'-'*38+'+',
                                        'MNIST DATA PROVIDER',
                                        'n_samples',
                                        self._n_samples,
                                        'n_batch',
                                        self._n_batches,
                                        'batch_size',
                                        self._batch_size,
                                        'shuffle',
                                        self.isShuffle,
                                        'one_hot',
                                        self.isOneHot)


class PaddedSeqProvider(object):

    def __init__(self, corpus_dir, dictionary_dir, label_map_dir, batch_size, max_word, isIndex = True, Padding = True):

        self.corpus_dir = corpus_dir
        self.dictionary_dir = dictionary_dir
        self.label_map_dir = label_map_dir
        self.batch_size = batch_size
        self.isIndex = isIndex
        self.max_word = max_word
        self.Padding = Padding
        if self.Padding == False:
            raise NotImplementedError
        self.loadCorpus()

    def reset(self):
        self._currentOrder = np.arange(self.n_samples)
        self.new_epoch()

    def new_epoch(self):
        np.random.shuffle(self._currentOrder)
        self._currentPosition = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._currentPosition >= self.n_batches:
            self.new_epoch()
            raise StopIteration
        lines = self.corpus[self._currentPosition*self.batch_size:(self._currentPosition + 1)*self.batch_size]
        batch_input_temp = [line.split()[1:self.max_word] for line in lines]
        batch_target_temp = [line.split()[0] for line in lines]
        if self.Padding == True:
            batch_input = np.zeros((self.batch_size, self.max_word, self.voc_size))
            batch_target = np.zeros((self.batch_size, self.n_classes))
        else:
            batch_input = np.zeros((len(batch_input_temp), self.max_word, self.voc_size))
            batch_target = np.zeros((len(batch_input_temp), self.n_classes))
        for i, j, k in zip(batch_input_temp, batch_target_temp, range(len(batch_input_temp))):
            batch_input[k] = self.sentence2vector(i)
            batch_target[k] = self.tagIndex2vector(j)
        self._currentPosition += 1
        return batch_input, batch_target

    def next(self):
        return self.__next__()

    def loadCorpus(self):
        try:
            self.corpus = open(self.corpus_dir, encoding='utf-8').readlines()
        except:
            self.corpus = open(self.corpus_dir, encoding='gbk').readlines()
        self.dictionary = pickle.load(open(self.dictionary_dir, 'rb'))
        self.label_map = pickle.load(open(self.label_map_dir, 'rb'))
        self.n_samples = len(self.corpus)
        self.voc_size = len(self.dictionary)
        self.n_classes = len(self.label_map)
        self._currentOrder = np.arange(self.n_samples)
        if (self.n_samples % self.batch_size) == 0:
            self.n_batches = int(self.n_samples / self.batch_size)
        else:
            self.n_batches = int(self.n_samples / self.batch_size) + 1
        self._currentPosition = 0

    def sentence2vector(self, indexes):
        res = np.array([self.vocIndex2vector(int(i)) for i in indexes])
        if self.Padding == True:
            n_padding = self.max_word - res.shape[0]
            res = np.concatenate([res, np.zeros((n_padding, self.voc_size))], 0)
        return res

    def vocIndex2vector(self, ids):
        res = np.zeros(self.voc_size)
        res[ids] = 1
        return res

    def tagIndex2vector(self, tags):
        res = np.zeros(self.n_classes)
        res[int(tags)] = 1
        return res

    def tag2tagIndex(self, tag):
        if self.isIndex:
            return int(tag)
        else:
            return int(self.label_map.index(int(tag)))

    def sentence2vocIndex(self, sentence):
        return [self.voc2vocIndex(word) for word in sentence]

    def voc2vocIndex(self, word):
        if self.isIndex == True:
            return int(word)
        else:
            return int(self.dictionary.index(word))

    def vocIndex2voc(self, index):
        return self.dictionary[index]

    def vocIndex2sentence(self, indexes):
        return [self.vocIndex2voc(wordIndex) for wordIndex in indexes]

    def tagIndex2tag(self, index):
        return self.label_map[index]


class BMWSeqProvider(object):

    def __init__(self, corpus_dir, batch_size = 50, max_word = 35, isGenerate = True, isTrain = False):

        self.corpus_dir = corpus_dir
        self.batch_size = batch_size
        self.max_word = max_word
        self.isGenerate = isGenerate
        self.isTrain = isTrain
        self._root_dir = '../../data/BMW/'
        self._prefix = 'seq_corpus_'
        # if self.Padding == False:
        #     raise NotImplementedError
        if self.isGenerate == True:
            self.loadCorpus()
        else:
            self.readCorpus()

    def reset(self):
        self._currentOrder = np.arange(self.n_samples)
        self.new_epoch()

    def new_epoch(self):
        np.random.shuffle(self._currentOrder)
        self._currentPosition = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._currentPosition >= self.n_batches:
            self.new_epoch()
            raise StopIteration
        # print(min((self._currentPosition + 1)*self.batch_size, self.n_samples))
        batch = [self.generateVec(i) for i in range(self._currentPosition*self.batch_size, min((self._currentPosition + 1)*self.batch_size, self.n_samples))]
        batch_sentence = []
        batch_intent = []
        batch_mention = []
        batch_intent_len = []
        batch_mention_len = []
        for sample in batch:
            batch_sentence.append(sample[0])
            batch_intent.append(sample[1])
            batch_mention.append(sample[2])
            batch_intent_len.append(sample[3])
            batch_mention_len.append(sample[4])

        batch_sentence = np.array(batch_sentence)
        batch_intent = np.array(batch_intent)
        batch_mention = np.array(batch_mention)
        batch_intent_len = np.array(batch_intent_len)
        batch_mention_len = np.array(batch_mention_len)
        self._currentPosition += 1
        return batch_sentence, batch_intent, batch_mention, batch_intent_len, batch_mention_len

    def next(self):
        return self.__next__()

    def loadCorpus(self):
        try:
            self.corpus = open(self.corpus_dir, encoding='utf-8').readlines()
        except:
            self.corpus = open(self.corpus_dir, encoding='gbk').readlines()

        self.corpus_ = dict()
        self.corpus_['sentences'] = []
        self.corpus_['intents'] = []
        self.corpus_['mentions'] = []
        self.corpus_['intents_len'] = []
        self.corpus_['mentions_len'] = []

        if self.isTrain == True:
            self.intent_set = set()
            self.mention_set = set()
            self.word_set = set()
        else:
            self.word_set = pickle.load(open(self._root_dir + self._prefix + 'vocabulary.npz', 'rb'))
            self.intent_set = pickle.load(open(self._root_dir + self._prefix + 'intent.npz', 'rb'))
            self.mention_set = pickle.load(open(self._root_dir + self._prefix + 'mention.npz', 'rb'))


        for line in self.corpus:
            sentence, intent, mention = line.split('#')
            sentence = sentence.split()
            intent = intent.split('.')
            mention = mention.split()
            self.corpus_['sentences'].append(sentence)
            self.corpus_['intents'].append(intent)
            self.corpus_['mentions'].append(mention)
            self.corpus_['intents_len'].append(len(intent))
            self.corpus_['mentions_len'].append(len(mention))

            if self.isTrain == True:
                for i in sentence:
                    self.word_set.add(i)
                for i in intent:
                    self.intent_set.add(i)
                for i in mention:
                    self.mention_set.add(i)
        if self.isTrain == True:
            self.word_set.add('OOV')

        self.corpus_['n_samples'] = len(self.corpus)
        self.corpus_['word_set'] = list(self.word_set)
        self.corpus_['intent_set'] = list(self.intent_set)
        self.corpus_['mention_set'] = list(self.mention_set)
        self.corpus_['n_word'] = len(self.word_set)
        self.corpus_['max_intent_len'] = np.max(self.corpus_['intents_len'])
        self.corpus_['n_intent'] = len(self.intent_set)
        self.corpus_['n_mention'] = len(self.mention_set)
        self.loadParameters()
        if self.isTrain == True:
            pickle.dump(self.corpus_, open(self._root_dir + self._prefix + 'train.npz', 'wb'))
            pickle.dump(self.word_set, open(self._root_dir + self._prefix + 'vocabulary.npz', 'wb'))
            pickle.dump(self.intent_set, open(self._root_dir + self._prefix + 'intent.npz', 'wb'))
            pickle.dump(self.mention_set, open(self._root_dir + self._prefix + 'mention.npz', 'wb'))
        else:
            pickle.dump(self.corpus_, open(self._root_dir + self._prefix + 'valid.npz', 'wb'))

    def readCorpus(self):
        if self.isTrain == True:
            self.corpus_ = pickle.load(open(self._root_dir + self._prefix + 'train.npz', 'rb'))
        else:
            self.corpus_ = pickle.load(open(self._root_dir + self._prefix + 'valid.npz', 'rb'))
        self.loadParameters()

    def loadParameters(self):

        self.n_samples = self.corpus_['n_samples']
        if self.isGenerate == True:
            self.word_set = self.corpus_['word_set']
            self.intent_set = self.corpus_['intent_set']
            self.mention_set = self.corpus_['mention_set']
        else:
            self.word_set = pickle.load(open(self._root_dir + self._prefix + 'vocabulary.npz', 'rb'))
            self.intent_set = pickle.load(open(self._root_dir + self._prefix + 'intent.npz', 'rb'))
            self.mention_set = pickle.load(open(self._root_dir + self._prefix + 'mention.npz', 'rb'))

        self.n_word = self.corpus_['n_word']
        self.max_intent_len = self.corpus_['max_intent_len']
        self.n_intent = self.corpus_['n_intent']
        self.n_mention = self.corpus_['n_mention']
        self._currentOrder = np.arange(self.n_samples)
        if (self.n_samples % self.batch_size) == 0:
            self.n_batches = int(self.n_samples / self.batch_size)
        else:
            self.n_batches = int(self.n_samples / self.batch_size) + 1
        self._currentPosition = 0

    def generateVec(self, index):
        sentence = self.corpus_['sentences'][index][:self.max_word]
        intent = self.corpus_['intents'][index]
        mention = self.corpus_['mentions'][index][:self.max_word]
        intent_len = self.corpus_['intents_len'][index]
        mention_len = self.corpus_['mentions_len'][index]
        sentence_vec = np.array([self.encoder(i, self.word_set, True) for i in sentence])
        intent_vec = np.array([self.encoder(i, self.intent_set, False) for i in intent])
        mention_vec = np.array([self.encoder(i, self.mention_set, False) for i in mention])
        return self.padding(sentence_vec, 'word'), self.padding(intent_vec, 'intent'), self.padding(mention_vec, 'mention'), intent_len, mention_len

    def padding(self, inputs, set_type):
        if set_type == 'word':
            return np.concatenate([inputs, np.zeros((self.max_word - len(inputs), self.n_word))], 0)
        elif set_type == 'intent':
            return np.concatenate([inputs, np.zeros((self.max_intent_len - len(inputs), self.n_intent))], 0)
        elif set_type == 'mention':
            return np.concatenate([inputs, np.zeros((self.max_word - len(inputs), self.n_mention))], 0)

    def encoder(self, inputs, close_set, isword):
        res = np.zeros(len(close_set))
        if isword == True:
            try:
                res[close_set.index(inputs)] = 1.
            except:
                res[close_set.index('OOV')] = 1.
        else:
            res[close_set.index(inputs)] = 1.
        return res

    def decoder(self, inputs, close_set, isword = False):
        pass



class VGGFaceProvider():
    # image_dir: directory of images
    # label_dir: directory of label
    #         sample: Name ID left upper right down pose DPM
    def __init__(self, image_dir, label_dir, batch_size, typename = 'jpg'):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.batch_size = batch_size
        self.typename = typename
        # self.name_id_dict = {}
        # print(self.image_dir)
        self.load()

    def load(self):
        print('[INFO] Starting to load dataset ...')
        self.image_filenames = [i for i in os.listdir(self.image_dir) if i.find(self.typename) != -1]
        if self.image_dir[-1] != '/':
            self.image_dir += '/'
        # print(self.image_dir)
        if len(self.image_filenames) == 0:
            print('[ERROR] BAD DIRECTORY')
            raise IOError
        shape = cv2.imread(self.image_dir + self.image_filenames[0]).shape
        self.lines = open(self.label_dir).readlines()
        # self.checkImg()
        self._n_samples = len(self.lines)
        self._n_batches = int(self._n_samples / self.batch_size)
        if self._n_samples % self.batch_size != 0:
            self._n_batches += 1
        self._currentPosition = 0
        self._currentOrder = np.arange(self._n_samples)
        # print(shape)
        print('[INFO] Dataset is ready .')

    def __iter__(self):
        return self

    def next(self):
        self.__next__()

    def __next__(self):
        if self._currentPosition >= self._n_batches:
            self.new_epoch()
            raise StopIteration
        indexes = self._currentOrder[self._currentPosition*self.batch_size:(self._currentPosition + 1)*self.batch_size]
        currentLines = [self.lines[i] for i in indexes]
        # print(indexes)
        batch_images = np.array([self.readImg(self.getImgURL(i)) for i in currentLines])
        # for img in batch_images:
        #     print(img.shape)
        batch_labels = np.array([[float(j) for j in i.split()[2:]] for i in currentLines])
        self._currentPosition += 1
        return batch_images, batch_labels

    def reset(self):
        self._currentOrder = np.arange(self._n_samples)
        self.new_epoch()

    def new_epoch(self):
        self.shuffle()
        self._currentPosition = 0

    def readImg(self, url):
        # print(url)
        # print('*'*50)
        return cv2.imread(url).astype(np.float32) / 255

    def checkImg(self):
        print('[INFO] Starting to check images and labels ...')
        for line in self.lines:
            filename = self.getImgURL(line)
            try:
                image = cv2.imread(filename)
                if len(image.shape) != 3 or len(image) == 0:
                    print('[ERROR] Broken Image Files: %s' % (filename))
                    raise IOError
            except:
                print('[ERROR] Broken Image Files: %s' % (filename))
                raise IOError
        print('[INFO] Images and labels checking has been finished .')

    def getImgURL(self, line):
        if self.typename[0] == '.':
            return self.image_dir + '+'.join(line.split()[:1]) + self.typename
        else:
            return self.image_dir + '+'.join(line.split()[:1]) + '.' + self.typename


    def shuffle(self):
        np.random.shuffle(self._currentOrder)










# if __name__ == '__main__':
#
#     provider = VGGFaceProvider('/home/cheng/github/TF_toolkit/data/FACE/reshape_images', '/home/cheng/github/TF_toolkit/data/FACE/reshape_labels.txt', 50, 'png')
#     for batch_inputs, batch_labels in provider:
#         print(batch_inputs.shape)
#         print(batch_labels.shape)
#
#         break

#     provider = BMWSeqProvider('../data/BMW/TEST.txt')
#     for batch in provider:
#         for i in range(5):
#             print(batch[i].shape)
        # break

#
#     provider = PaddedSeqProvider('../data/anonymous_raw_poi_valid_trimmed.txt', '../data/raw_poiwords.dict', '../data/raw_poilabel_map.npz', 50, 35)
#     i = 0
#     for batch_input, batch_target in provider:
#         print(batch_input.shape, batch_target.shape)
#         i += 1
#         # break
#     print(i)
#     print(provider.n_samples / 50)











#     provider = CIFARProvider('../data/cifar-10-train.npz', 50)
#     temp = 0
#     for inputs, targets in provider:
#         print(inputs.shape, targets.shape)
#         temp += 1
#         if temp == 2:
#             break
#     import matplotlib.pyplot as plt
#     # print(inputs[0].reshape(3,32,32).transpose([1,2,0]))
#     for i in range(50):
#         # print(targets[i])
#         # print(provider._label_map)
#         plt.imshow(np.array(inputs[i], dtype = np.float32))
#         plt.title(provider._label_map[np.argmax(targets[i])])
#         plt.show()
#
#     provider = MNISTProvider('../data/mnist-train.npz', 50)
#     provider.shuffle()
#     print(provider.inputs.shape)
#     for train, valid in provider:
#         print(provider)
#         print(train.shape, valid.shape)
