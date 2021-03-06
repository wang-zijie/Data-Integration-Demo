import tensorflow as tf
import argparse
import os
import numpy as np
import heapq
from model.word_cnn import WordCNN
from utils.data_utils import batch_iter, test_data_word2vec,train_data_word2vec,load_word2vec_matrix
from sklearn.metrics import average_precision_score,accuracy_score

import time

NUM_CLASS = 460
NUM_LABEL = 2
BATCH_SIZE = 256
NUM_EPOCHS = 50
MAX_DOCUMENT_LEN = 15
num_train = 28751
num_test = 28751


def get_onehot_label_topk(scores, top_num,threshold = 0.8):
    '''

    get the top k score from testing result,
    use threshold to filter the irrelevant data.

    :param scores:  predicted scores for each classification class
    :param top_num: number of labels for each data(corrosponding to top k scores)
    :param threshold: score of irrelevant data < threshold

    :return:
        predicted_onehot_labels: Predict labels (onehot format)
    '''
    predicted_onehot_labels = []
    scores = np.ndarray.tolist(scores)
    for score in scores:
        count = 0
        onehot_labels_list = [0] * len(score)
        max_num_index_list = list(map(score.index, heapq.nlargest(top_num, score)))
        for index, predict_score in enumerate(score):
            if predict_score >= threshold:

                count += 1
        if count < NUM_LABEL:

            onehot_labels_list[457] = 1
            onehot_labels_list[458] = 1
            onehot_labels_list[459] = 1
            predicted_onehot_labels.append(onehot_labels_list)
        else:
            for i in max_num_index_list:
                onehot_labels_list[i] = 1
            predicted_onehot_labels.append(onehot_labels_list)

    return predicted_onehot_labels


def train(train_x, train_y, test_x, test_y, vocabulary_size, args):
    with tf.Session() as sess:
        model = WordCNN(vocabulary_size, MAX_DOCUMENT_LEN, NUM_CLASS)

        # Define training procedure
        global_step = tf.Variable(0, trainable=False)
        params = tf.trainable_variables()
        gradients = tf.gradients(model.loss, params)
        clipped_gradients, _ = tf.clip_by_global_norm(gradients, 5.0)
        optimizer = tf.train.AdamOptimizer(model.learning_rate)
        train_op = optimizer.apply_gradients(zip(clipped_gradients, params), global_step=global_step)

        # Initialize all variables
        sess.run(tf.global_variables_initializer())


        def train_step(batch_x, batch_y):
            feed_dict = {
                model.x: batch_x,
                model.y: batch_y,
                model.keep_prob: 0.8,
            }
            _, step, loss = sess.run([train_op, global_step, model.loss], feed_dict=feed_dict)

            return loss

        def test_accuracy(test_x, test_y):
            '''

            :param test_x:
            :param test_y:
            :return:
                eval_loss: loss
                acc: accuracy
                eval_prc: average precison
                eval_pre_tk: precision
                eval_rec_tk: recall
                eval_F1_tk: F1 score
            '''

            true_onehot_labels = []
            predicted_onehot_scores = []


            predicted_onehot_labels_t2 = []

            test_batches = batch_iter(test_x, test_y, BATCH_SIZE, 1)
            eval_loss, eval_counter = 0., 0

            for test_batch_x, test_batch_y in test_batches:
                scores, cur_loss = sess.run([model.scores, model.loss],
                                            feed_dict={model.x: test_batch_x, model.y: test_batch_y,
                                                       model.keep_prob: 1.0})

                for i in test_batch_y:
                    true_onehot_labels.append(i)
                for j in scores:
                    predicted_onehot_scores.append(j)

                batch_predicted_onehot_labels = get_onehot_label_topk(scores=scores, top_num=NUM_LABEL)

                for i in batch_predicted_onehot_labels:
                    predicted_onehot_labels_t2.append(i)

                eval_loss = eval_loss + cur_loss
                eval_counter = eval_counter + 1

            #metrics
            eval_loss = float(eval_loss / eval_counter)

            acc = accuracy_score(np.array(true_onehot_labels), np.array(predicted_onehot_labels_t2))

            eval_prc = average_precision_score(y_true=np.array(true_onehot_labels),
                                              y_score=np.array(predicted_onehot_scores), average='micro')



            return eval_loss, acc, eval_prc

        # Training loop
        batches = batch_iter(train_x, train_y, BATCH_SIZE, NUM_EPOCHS)

        st = time.time()
        steps_per_epoch = int(num_train / BATCH_SIZE)
        for batch_x, batch_y in batches:
            step = tf.train.global_step(sess, global_step)
            num_epoch = int(step / steps_per_epoch)
            #curr_lr = sess.run(model.lr)

            loss = train_step(batch_x, batch_y)


            if step % 50 == 0:

                eval_loss, acc, eval_prc = test_accuracy(test_x, test_y)

                mode = "w" if step == 0 else "a"
                with open(args.summary_dir + "-accuracy.txt", mode) as f:
                   print("epo: {}, step: {}, loss: {}, accuracy: {}".format(num_epoch, step, eval_loss, acc), file=f)


                print("epoch: {}, step: {}, loss: {}, steps_per_epoch: {}, batch size: {}".
                     format(num_epoch, step, eval_loss, steps_per_epoch, BATCH_SIZE))
                print("Accuracy:{}, loss:{}, ave_pre:{}".format(acc,eval_loss,eval_prc))
                print("time of one epoch: {}\n".format(time.time()-st))
        st = time.time()

        eval_loss, acc, eval_prc = test_accuracy(test_x, test_y)
        print('test time',time.time()-st)
        print(eval_loss,acc)

if __name__ == "__main__":
    stt = time.time()

    parser = argparse.ArgumentParser()

    parser.add_argument("--summary_dir", type=str, default="summary_classifier", help="summary dir.")

    args = parser.parse_args()


    os.environ['CUDA_VISIBLE_DEVICES'] = '0'

    print("\n Building dictionary..")

    t = time.time()
    word_dict = build_word_dict()
    print("Preprocessing dataset..")
    train_x, train_y = build_word_dataset("train", word_dict,NUM_CLASS ,MAX_DOCUMENT_LEN)
    test_x, test_y = build_word_dataset("test", word_dict, NUM_CLASS,MAX_DOCUMENT_LEN)
    print('data preprocessing time: {}'.format(time.time() - t))
    assert len(train_x) == len(train_y)
    assert len(test_x) == len(test_y)
    print("length of train_x: {}, length of test_x: {}".format(len(train_x), len(test_x)))
    print("length of word_dict: {}".format(len(word_dict)))


    t1 = time.time()
    train(train_x, train_y, test_x, test_y, len(word_dict), args)
    print('training time+test time: {}', format(time.time() - t1))

    print("total time: {}".format(time.time() - stt))


