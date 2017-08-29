from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import argparse
import tensorflow as tf
import pandas as pd

from EUNN import EUNNCell
from GORU_revised import GORUCell

def copying_data(T, n_data, n_sequence):
    seq = np.random.randint(1, high=9, size=(n_data, n_sequence))
    zeros1 = np.zeros((n_data, T-1))
    zeros2 = np.zeros((n_data, T))
    marker = 9 * np.ones((n_data, 1))
    zeros3 = np.zeros((n_data, n_sequence))

    x = np.concatenate((seq, zeros1, marker, zeros3), axis=1).astype('int32')
    y = np.concatenate((zeros3, zeros2, seq), axis=1).astype('int64')
    
    return x, y

def main(model, T, n_iter, n_batch, n_hidden, capacity, comp, fft):

    # --- Set data params ----------------
    n_input = 10
    n_output = 9
    n_sequence = 10
    n_train = n_iter * n_batch
    n_test = n_batch

    n_input = 10
    n_steps = T+20
    n_classes = 9


    # --- Create graph and compute gradients ----------------------
    x = tf.placeholder("int32", [None, n_steps])
    y = tf.placeholder("int64", [None, n_steps])
    
    input_data = tf.one_hot(x, n_input, dtype=tf.float32)



    # --- Input to hidden layer ----------------------
    if model == "LSTM":
        cell = tf.nn.rnn_cell.BasicLSTMCell(n_hidden, state_is_tuple=True, forget_bias=1)
        hidden_out, _ = tf.nn.dynamic_rnn(cell, input_data, dtype=tf.float32)
    elif model == "GRU":
        cell = tf.nn.rnn_cell.GRUCell(n_hidden)
        hidden_out, _ = tf.nn.dynamic_rnn(cell, input_data, dtype=tf.float32)
    elif model == "EUNN":
        cell = EUNNCell(n_hidden, capacity, fft, comp)
        if comp:
            hidden_out_comp, _ = tf.nn.dynamic_rnn(cell, input_data, dtype=tf.complex64)
            hidden_out = tf.real(hidden_out_comp)
        else:
            hidden_out, _ = tf.nn.dynamic_rnn(cell, input_data, dtype=tf.float32)
    elif model == "GORU":
        cell = GORUCell(n_hidden, capacity, fft)
        hidden_out, _ = tf.nn.dynamic_rnn(cell, input_data, dtype=tf.float32)

    # --- Hidden Layer to Output ----------------------
    V_init_val = np.sqrt(6.)/np.sqrt(n_output + n_input)

    V_weights = tf.get_variable("V_weights", shape = [n_hidden, n_classes], \
            dtype=tf.float32, initializer=tf.random_uniform_initializer(-V_init_val, V_init_val))
    V_bias = tf.get_variable("V_bias", shape=[n_classes], \
            dtype=tf.float32, initializer=tf.constant_initializer(0.01))

    hidden_out_list = tf.unstack(hidden_out, axis=1)
    temp_out = tf.stack([tf.matmul(i, V_weights) for i in hidden_out_list])
    output_data = tf.nn.bias_add(tf.transpose(temp_out, [1,0,2]), V_bias) 

    # --- evaluate process ----------------------
    cost = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=output_data, labels=y))
    correct_pred = tf.equal(tf.argmax(output_data, 2), y)
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))


    # --- Initialization ----------------------
    optimizer = tf.train.RMSPropOptimizer(learning_rate=0.001, decay=0.9).minimize(cost)
    init = tf.global_variables_initializer()



    # --- baseline ----------------------
    baseline = np.log(8) * 10/(T+20)
    print("Baseline is " + str(baseline))


    # --- Training Loop ----------------------


    config = tf.ConfigProto()
    #config.gpu_options.per_process_gpu_memory_fraction = 0.2
    config.log_device_placement = False
    config.allow_soft_placement = False
    with tf.Session(config=config) as sess:

    # --- Create data --------------------

        train_x, train_y = copying_data(T, n_train, n_sequence)
        test_x, test_y = copying_data(T, n_test, n_sequence)



        sess.run(init)
        
        step = 0
        step_list = []
        loss_list = []
        acc_list = []
        while step < n_iter:
            step_list.append(step)
            batch_x = train_x[step * n_batch : (step+1) * n_batch]
            batch_y = train_y[step * n_batch : (step+1) * n_batch]

            sess.run(optimizer, feed_dict={x: batch_x, y: batch_y})

            acc, loss = sess.run([accuracy, cost], feed_dict={x: batch_x, y: batch_y})

            if step%500 == 0:
                print(" Iter " + str(step) + ", Minibatch Loss= " + "{:.6f}".format(loss) + ", Training Accuracy= " + "{:.5f}".format(acc))

            loss_list.append(loss)
            acc_list.append(acc)
            step += 1

        df = pd.DataFrame(data={'step':step_list, 'train_loss':loss_list,
                                'train_acc': acc_list})
        df.to_csv('./' + 'copying_task_train_GORU.csv')

        print("Optimization Finished!")


        
        # --- test ----------------------

        test_acc = sess.run(accuracy, feed_dict={x: test_x, y: test_y})
        test_loss = sess.run(cost, feed_dict={x: test_x, y: test_y})
        df2 = pd.DataFrame(data={'test_loss':[test_loss],
                                'test_acc': [test_acc]})
        df2.to_csv('./' + 'copying_task_test_GORU.csv')
        print("Test result: Loss= " + "{:.6f}".format(test_loss) + ", Accuracy= " + "{:.5f}".format(test_acc))


if __name__=="__main__":

        
    kwargs = {    
                'model': "GORU",                #'Model name: [LSTM, GRU, EUNN, GORU]
                'T': 100,                       #Copying Problem delay: [int]
                'n_iter': 20000,                 #training iteration number:[int]
                'n_batch': 128,                 #batch size:[int]
                'n_hidden': 128,                #hidden layer size:[int]
                'capacity': 2,                  #Tunable style capacity, default value is 2:[int]
                'comp': False,                  #Complex domain or Real domain, only for EUNN. Default is False: complex domain:[bool]
                'fft': False,                   #fft style, only for EUNN and GORU, default is False: tunable style:[bool]
            }

    main(**kwargs)