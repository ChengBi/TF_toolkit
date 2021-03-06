import json
import tensorflow as tf
from config_mapping import *
from tools import *
from data_provider import *
# from cmd_io import *
from logging_io import *
import shutil
import os
from tensorflow.contrib.seq2seq import *
from tensorflow.python.layers.core import Dense
import sys
from tools import *

def basic_builder(data_conf_dir, model_conf_dir, data_provider, round_val=5, saveLOG=True, needSummary = False, isAutoEncoder = False):

    data_conf = json.load(open(data_conf_dir, 'r'))
    model_conf = json.load(open(model_conf_dir, 'r'))
    graph_assertion(model_conf['layers'])
    # savemode_assertion(model_conf['save_mode'])
    # save_mode = model_conf['save_mode']
    train_provider = data_provider(data_conf['training_filename'], data_conf['batch_size'], isShuffle = bool(data_conf['shuffle']), isAutoEncoder = isAutoEncoder)
    valid_provider = data_provider(data_conf['validation_filename'], data_conf['batch_size'], isShuffle = bool(data_conf['shuffle']), isAutoEncoder = isAutoEncoder)
    assert(isinstance(train_provider, dataProvider))
    assert(isinstance(valid_provider, dataProvider))
    log = {
        'train':{
            'acc':[],
            'err':[]
        },
        'valid':{
            'acc':[],
            'err':[]
        },
        'test':{
            'acc':[],
            'err':[]
        }
    }
    bestModels_id = []
    iteration = model_conf['iteration']
    interval = model_conf['interval']
    run_mode_assertion(model_conf['run_mode'])
    run_mode = model_conf['run_mode']

    if run_mode == 'train':
        try:
            os.mkdir('models')
            os.mkdir('nice_models')
            logging_io.SUCCESS_INFO('Directory:[models] and [nice_models] have been created succesfully!')
            logging_io.DEBUG_INFO('Running in training mode!')
        except:
            logging_io.WARNING_INFO('Directories have already been exists, please make sure whether they should be overwritten!')
            return
    else:
        logging_io.DEBUG_INFO('Running in validation mode!')

    graph = tf.Graph()
    with graph.as_default():
        layers = dict()
        outputs = dict()
        placeholder = dict()
        inputs_placeholder = placeholder_mapping(model_conf['inputs_placeholder'])
        placeholder['inputs_placeholder'] = inputs_placeholder
        targets_placeholder = placeholder_mapping(model_conf['targets_placeholder'])
        placeholder['targets_placeholder'] = targets_placeholder
        outputs['inputs_placeholder'] = inputs_placeholder

        for key in model_conf['layers'].keys():
            layers[key] = layers_mapping(key, model_conf['layers'][key])
            logging_io.BUILD_INFO(layers[key])
        for layer_name, layer in layers.items():
            outputs[layer_name] = layer.outputs(outputs[model_conf['layers'][layer_name]['inputs']])

        # logging_io.WARNING_INFO(outputs['outputs'])
        # logging_io.WARNING_INFO(targets_placeholder)
        logging_io.WARNING_INFO('SUMMARY ASSERTION BEGIN')
        summary_assertion(model_conf, needSummary)
        logging_io.WARNING_INFO('SUMMARY ASSERTION END')

        loss = loss_mean(outputs['outputs'], targets_placeholder, model_conf)
        logging_io.BUILD_INFO(loss)
        optimizer = optimizer_mapping(model_conf['optimizer']).minimize(loss)
        logging_io.BUILD_INFO(optimizer)
        accuracy = acc_sum(outputs["outputs"], targets_placeholder)
        logging_io.BUILD_INFO(accuracy)
        sess = tf.Session()
        if needSummary:
            tf.summary.scalar('mean_loss', loss)
            tf.summary.scalar('accuracy', accuracy)
            merged_all = tf.summary.merge_all()
            train_writer = tf.summary.FileWriter('tensorboard/train', sess.graph)
            valid_writer = tf.summary.FileWriter('tensorboard/valid')
        if run_mode == 'train':
            sess.run(tf.global_variables_initializer())
            saver = tf.train.Saver(write_version = tf.train.SaverDef.V1)
        else:
            saver = tf.train.Saver()
            model_id = pickle.load(open('model_ids.npz', 'rb'))
            saver.restore(sess, 'nice_models/model.ckpt-' + str(model_id[-1]))
            iteration = 1

        for i in range(iteration):
            current_id = i + 1
            errs = 0
            accs = 0
            for batch_train_inputs, batch_train_targets in train_provider:
                if run_mode == 'train':
                    if needSummary:
                        _, err, acc, merge = sess.run([optimizer, loss, accuracy, merged_all], feed_dict = {inputs_placeholder:batch_train_inputs, targets_placeholder:batch_train_targets})
                    else:
                        _, err, acc = sess.run([optimizer, loss, accuracy], feed_dict = {inputs_placeholder:batch_train_inputs, targets_placeholder:batch_train_targets})
                else:
                    if needSummary:
                        err, acc, merge = sess.run([loss, accuracy, merged_all], feed_dict = {inputs_placeholder:batch_train_inputs, targets_placeholder:batch_train_targets})
                    else:
                        err, acc = sess.run([loss, accuracy], feed_dict = {inputs_placeholder:batch_train_inputs, targets_placeholder:batch_train_targets})
                errs += err
                accs += acc
            log['train']['err'].append(round(errs/train_provider.n_batches(), round_val))
            log['train']['acc'].append(round(accs/train_provider.n_samples(), round_val))
            if needSummary:
                train_writer.add_summary(merge, i)
            logging_io.RESULT_INFO('Epoch {0:5} Training LOSS: {1:5} Training ACC: {2:5}'.format(current_id, log['train']['err'][-1], log['train']['acc'][-1]))
            if run_mode == 'train':
                save_path = saver.save(sess, 'models/' + 'model.ckpt', global_step=current_id)
                logging_io.DEBUG_INFO('Models have been saved in {0}'.format(save_path))

            if (current_id) % interval == 0 or run_mode == 'valid':
                errs = 0
                accs = 0
                for batch_valid_inputs, batch_valid_targets in valid_provider:
                    if needSummary:
                        err, acc, merge = sess.run([loss, accuracy, merged_all], feed_dict = {inputs_placeholder:batch_valid_inputs, targets_placeholder:batch_valid_targets})
                    else:
                        err, acc = sess.run([loss, accuracy], feed_dict = {inputs_placeholder:batch_valid_inputs, targets_placeholder:batch_valid_targets})
                    errs += err
                    accs += acc
                log['valid']['err'].append(round(errs/valid_provider.n_batches(), round_val))
                log['valid']['acc'].append(round(accs/valid_provider.n_samples(), round_val))
                if run_mode == 'train':
                    if log['valid']['acc'][-1] >= np.max(log['valid']['acc']):
                        bestModels_id.append(current_id)
                        shutil.copy('models/model.ckpt-'+str(current_id), 'nice_models/model.ckpt-'+str(current_id))
                        shutil.copy('models/model.ckpt-'+str(current_id) + '.meta', 'nice_models/model.ckpt-'+str(current_id) + '.meta')
                if needSummary:
                    valid_writer.add_summary(merge, i)
                logging_io.RESULT_INFO('Epoch {0:5} validation LOSS: {1:5} validation ACC: {2:5}'.format(current_id, log['valid']['err'][-1], log['valid']['acc'][-1]))
            logging_io.LOG_COLLECTOR('LOGS')
    if run_mode == 'train':
        pickle.dump(bestModels_id, open('model_ids.npz', 'wb'))
    return log

'''
def autoencoder_builder(data_conf_dir, model_conf_dir, data_provider, round_val=5, saveLOG=True):

    data_conf = json.load(open(data_conf_dir, 'r'))
    model_conf = json.load(open(model_conf_dir, 'r'))
    graph_assertion(model_conf['layers'])
    train_provider = data_provider(data_conf['training_filename'], data_conf['batch_size'], isShuffle = bool(data_conf['shuffle']))
    valid_provider = data_provider(data_conf['validation_filename'], data_conf['batch_size'], isShuffle = bool(data_conf['shuffle']))
    assert(isinstance(train_provider, dataProvider))
    assert(isinstance(valid_provider, dataProvider))
    log = {
        'train':{
            'err':[]
        },
        'valid':{
            'err':[]
        },
        'test':{
            'err':[]
        }
    }
    iteration = model_conf['iteration']
    interval = model_conf['interval']
    run_mode = model_conf['run_mode']

    graph = tf.Graph()
    with graph.as_default():

        layers = dict()
        outputs = dict()
        placeholder = dict()

        inputs_placeholder = placeholder_mapping(model_conf['inputs_placeholder'])
        placeholder['inputs_placeholder'] = inputs_placeholder
        logging_io.DEBUG_INFO('Runing in autoencoder mode!')
        outputs['inputs_placeholder'] = inputs_placeholder

        for key in model_conf['layers'].keys():
            layers[key] = layers_mapping(key, model_conf['layers'][key])
            logging_io.BUILD_INFO(layers[key])
        for layer_name, layer in layers.items():
            outputs[layer_name] = layer.outputs(outputs[model_conf['layers'][layer_name]['inputs']])

        loss = loss_mean(outputs['outputs'], inputs_placeholder, model_conf)
        logging_io.BUILD_INFO(loss)
        optimizer = optimizer_mapping(model_conf['optimizer']).minimize(loss)
        logging_io.BUILD_INFO(optimizer)

        if run_mode == 'train':
            sess = tf.Session()
            sess.run(tf.global_variables_initializer())
            for i in range(iteration):
                errs = 0
                # accs = 0
                for batch_train_inputs, batch_train_targets in train_provider:
                    _, err = sess.run([optimizer, loss], feed_dict = {inputs_placeholder:batch_train_inputs})
                    errs += err
                log['train']['err'].append(round(errs/train_provider.n_batches(), round_val))
                logging_io.RESULT_INFO('Epoch {0:5} Training LOSS: {1:5}'.format(i, log['train']['err'][-1]))
                if (i+1) % interval == 0:
                    errs = 0
                    for batch_valid_inputs, batch_valid_targets in valid_provider:
                        err = sess.run([loss], feed_dict = {inputs_placeholder:batch_valid_inputs})
                        errs += err[0]
                    log['valid']['err'].append(round(errs/valid_provider.n_batches(), round_val))
                    logging_io.RESULT_INFO('Epoch {0:5} validation LOSS: {1:5}'.format(i, log['valid']['err'][-1]))
        elif run_mode == 'valid':
            errs = 0
            for batch_train_inputs, batch_train_targets in train_provider:
                err = sess.run([loss], feed_dict = {inputs_placeholder:batch_train_inputs})
                errs += err
            log['train']['err'].append(round(errs/train_provider.n_batches(), round_val))
            logging_io.RESULT_INFO('Epoch {0:5} Training LOSS: {1:5}'.format(i, log['train']['err'][-1]))
            errs = 0
            for batch_valid_inputs, batch_valid_targets in valid_provider:
                err = sess.run([loss], feed_dict = {inputs_placeholder:batch_valid_inputs})
                errs += err
            log['valid']['err'].append(round(errs/valid_provider.n_batches(), round_val))
            logging_io.RESULT_INFO('Epoch {0:5} validation LOSS: {1:5}'.format(i, log['valid']['err'][-1]))

        if saveLOG == True:
            logging_io.LOG_COLLECTOR('LOGS')
    return log
'''

class Model(object):

    def __init__(self):
        pass


class Seq2SeqModel(object):

    def __init__(self, rnn_size, layer_size, encoder_vocab_size,
        decoder_vocab_size, embedding_dim, grad_clip, is_inference=False):
        # define inputs
        self.input_x = tf.placeholder(tf.int32, shape=[None, None], name='input_ids')

        # define embedding layer
        with tf.variable_scope('embedding'):
            encoder_embedding = tf.Variable(tf.truncated_normal(shape=[encoder_vocab_size, embedding_dim], stddev=0.1),
                name='encoder_embedding')
            decoder_embedding = tf.Variable(tf.truncated_normal(shape=[decoder_vocab_size, embedding_dim], stddev=0.1),
                name='decoder_embedding')

        # define encoder
        with tf.variable_scope('encoder'):
            encoder = self._get_simple_lstm(rnn_size, layer_size)

        with tf.device('/cpu:0'):
            input_x_embedded = tf.nn.embedding_lookup(encoder_embedding, self.input_x)

        encoder_outputs, encoder_state = tf.nn.dynamic_rnn(encoder, input_x_embedded, dtype=tf.float32)

        # define helper for decoder
        if is_inference:
            self.start_tokens = tf.placeholder(tf.int32, shape=[None], name='start_tokens')
            self.end_token = tf.placeholder(tf.int32, name='end_token')
            # self.start_tokens = start
            # self.end_token = end
            # logging_io.WARNING_INFO(str(self.start_tokens))
            # logging_io.WARNING_INFO(str(self.end_token))
            helper = GreedyEmbeddingHelper(decoder_embedding, self.start_tokens, self.end_token)
        else:
            self.target_ids = tf.placeholder(tf.int32, shape=[None, None], name='target_ids')
            self.decoder_seq_length = tf.placeholder(tf.int32, shape=[None], name='batch_seq_length')
            with tf.device('/cpu:0'):
                target_embeddeds = tf.nn.embedding_lookup(decoder_embedding, self.target_ids)
            helper = TrainingHelper(target_embeddeds, self.decoder_seq_length)

        with tf.variable_scope('decoder'):
            fc_layer = Dense(decoder_vocab_size)
            decoder_cell = self._get_simple_lstm(rnn_size, layer_size)
            decoder = BasicDecoder(decoder_cell, helper, encoder_state, fc_layer)

        logits, final_state, final_sequence_lengths = dynamic_decode(decoder)

        if not is_inference:
            targets = tf.reshape(self.target_ids, [-1])
            logits_flat = tf.reshape(logits.rnn_output, [-1, decoder_vocab_size])
            print('shape logits_flat:{}'.format(logits_flat.shape))
            print('shape logits:{}'.format(logits.rnn_output.shape))

            self.cost = tf.losses.sparse_softmax_cross_entropy(targets, logits_flat)

            # define train op
            tvars = tf.trainable_variables()
            grads, _ = tf.clip_by_global_norm(tf.gradients(self.cost, tvars), grad_clip)

            optimizer = tf.train.AdamOptimizer(1e-3)
            self.train_op = optimizer.apply_gradients(zip(grads, tvars))
        else:
            self.prob = tf.nn.softmax(logits)

    def _get_simple_lstm(self, rnn_size, layer_size):
        lstm_layers = [tf.contrib.rnn.LSTMCell(rnn_size) for _ in np.arange(layer_size)]
        return tf.contrib.rnn.MultiRNNCell(lstm_layers)

if __name__ == '__main__':
    corpus_dir = '../../Basic_Tensorflow/corpus/'
    # label_map = pickle.load(open(corpus_dir + 'raw_poilabel_map.npz', 'rb'))
    # dictionary = pickle.load(open(corpus_dir + 'raw_poiwords.dict', 'rb'))

    label_map = pickle.load(open(corpus_dir + 'label_map.npz', 'rb'))
    dictionary = pickle.load(open(corpus_dir + 'words.dict', 'rb'))
    max_word = 35
    voc_size = len(dictionary)
    embedding_size = 128
    # provider = idProvider(corpus_dir + 'anonymous_raw_poi_train.txt', 50) #anonymous_raw_poi_train.txt
    provider = idProvider(corpus_dir + 'anouymous_corpus_full_train.txt', 50) #.txt



    graph = tf.Graph()
    with graph.as_default():

        # model = Seq2SeqModel(64, 1, voc_size, voc_size, 100, 10, False)
        # saver = tf.train.Saver(write_version = tf.train.SaverDef.V1)
        # sess = tf.Session()
        # sess.run(tf.global_variables_initializer())
        # for i in range(1):
        #     for length, batch_input, batch_targets in provider:
        #         feed_dict = {model.input_x:batch_input, model.target_ids:batch_input, model.decoder_seq_length:[length]*len(batch_input)}
        #         _, loss = sess.run([model.train_op, model.cost], feed_dict = feed_dict)
        #         break
        #     logging_io.DEBUG_INFO('LOSS is ' + str(loss))
        # saver.save(sess, '../models/model.ckpt', global_step=i)
    #     start = dictionary.index('<BEGIN>')
    #     end = dictionary.index('<END>')
    #     sess1 = tf.Session()
    #     model2 = Seq2SeqModel(64, 1, voc_size, voc_size, 100, 10, [start], end, is_inference = True)
    #     saver1 = tf.train.Saver()
    #     saver1.restore(sess1, '../models/model.ckpt-0')
    # # if 1 == 1:
    #     while(True):
    #         sentence = str(input('sentence: '))
    #         if sentence == 'q':
    #             sys.exit()
    #         ids = raw2ids('<BEGIN> '+' '.join([s for s in sentence])+' <END>')
    #         p = sess1.run([mode2.prob], feed_dict = {model2.input_x: [ids]})
    #         print(p)
        # print(dictionary.index('<END>'))
        # print(dictionary.index('<BEGIN>'))
