from __future__ import absolute_import
from __future__ import division
from __future__	import print_function

import numpy as np
import argparse, os
import tensorflow as tf
import pandas as pd

from EUNN import EUNNCell
from GORU_revised import GORUCell


def paren_data(T, n_data):
	MAX_COUNT = 10
	n_paren = 10
	n_noise = 10

	inputs = (np.random.rand(T, n_data)* (n_paren * 2 + n_noise)).astype(np.int32)
	counts = np.zeros((n_data, n_paren), dtype=np.int32)
	targets = np.zeros((T, n_data, n_paren), dtype = np.int32)
	opening_parens = (np.arange(0, n_paren)*2)[None, :]
	closing_parens = opening_parens + 1
	for i in range(T):
		opened = np.equal(inputs[i, :, None], opening_parens)
		counts = np.minimum(MAX_COUNT, counts + opened)
		closed = np.equal(inputs[i, :, None], closing_parens)
		counts = np.maximum(0, counts - closed)
		targets[i, :, :] = counts


	x = np.transpose(inputs, [1,0])
	y = np.transpose(targets, [1,0,2])

	return x, y


def main(model, T, n_iter, n_batch, n_hidden, capacity, comp, fft):

	# --- Set data params ----------------
	n_input = 30
	n_output = 10
	n_test = 10000

	n_steps = T
	n_classes = 21



	# --- Create graph and compute gradients ----------------------
	x = tf.placeholder("int32", [None, n_steps])
	y = tf.placeholder("int64", [None, n_steps, n_output])
	
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

	V_weights = tf.get_variable("V_weights", shape = [n_hidden, n_classes * n_output], dtype=tf.float32, initializer=tf.random_uniform_initializer(-V_init_val, V_init_val))
	V_bias = tf.get_variable("V_bias", shape=[n_classes * n_output], dtype=tf.float32, initializer=tf.constant_initializer(0.01))

	hidden_out_list = tf.unstack(hidden_out, axis=1)
	temp_out = tf.stack([tf.matmul(i, V_weights) for i in hidden_out_list])
	output_data = tf.reshape(tf.nn.bias_add(tf.transpose(temp_out, [1,0,2]), V_bias), [-1, n_steps, n_output, n_classes]) 

	# --- evaluate process ----------------------
	cost = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=output_data, labels=y))
	correct_pred = tf.equal(tf.argmax(output_data, 3), y)
	accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))


	# --- Initialization ----------------------
	optimizer = tf.train.AdamOptimizer(learning_rate=0.001).minimize(cost)
	init = tf.global_variables_initializer()

	# --- Training Loop ----------------------

	step = 0
	step_list = []
	loss_list = []
	acc_list = []
	with tf.Session(config=tf.ConfigProto(log_device_placement=False, allow_soft_placement=False)) as sess:

		sess.run(init)



		while step < n_iter:
			step_list.append(step)
			batch_x, batch_y = paren_data(T, n_batch)
			
			sess.run(optimizer, feed_dict={x: batch_x, y: batch_y})

			acc, loss = sess.run([accuracy, cost], feed_dict={x: batch_x, y: batch_y})
			if step%500 == 0:
				print("Iter " + str(step) + ", Minibatch Loss= " + \
					  "{:.6f}".format(loss) + ", Training Accuracy= " + \
					  "{:.5f}".format(acc))

			loss_list.append(loss)
			acc_list.append(acc)
			df = pd.DataFrame(data={'step':step_list, 'train_loss':loss_list,'train_acc': acc_list})
			df.to_csv('./' + 'paren_task_train_GRU.csv')
			step += 1


		print("Optimization Finished!")


		
		# --- test ----------------------
		test_x, test_y = paren_data(T, n_test)

		test_acc = sess.run(accuracy, feed_dict={x: test_x, y: test_y})
		test_loss = sess.run(cost, feed_dict={x: test_x, y: test_y})
		df2 = pd.DataFrame(data={'test_loss':[test_loss],'test_acc': [test_acc]})
		df2.to_csv('./' + 'paren_task_test_GRU.csv')
		print("Test result: Loss= " + "{:.6f}".format(test_loss) + ", Accuracy= " + "{:.5f}".format(test_acc))


if __name__=="__main__":



    kwargs = {    
                'model': "GRU",                #'Model name: [LSTM, GRU, EUNN, GORU]
                'T': 100,                       #Copying Problem delay: [int]
                'n_iter': 20000,                 #training iteration number:[int]
                'n_batch': 128,                 #batch size:[int]
                'n_hidden': 128,                #hidden layer size:[int]
                'capacity': 2,                  #Tunable style capacity, default value is 2:[int]
                'comp': False,                  #Complex domain or Real domain, only for EUNN. Default is False: complex domain:[bool]
                'fft': False,                   #fft style, only for EUNN and GORU, default is False: tunable style:[bool]
            }

    main(**kwargs)