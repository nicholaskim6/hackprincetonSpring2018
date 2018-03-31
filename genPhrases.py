import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.contrib import rnn
from tensorflow.python.ops import control_flow_ops
from tqdm import tqdm
from pre import sample as sampleData



def randSparseTensor(shape):
  return np.round(np.random.rand(shape[0], shape[1]))

note_range = 470 # num of notes
# this file generates phrases based on input phrases 
def getPhrases(test=False):
  if test:
    amtSample = 10
    return list(("CLASSIFICATION", randSparseTensor((512,note_range))) for _ in range(amtSample))
  return sampleData()

phrases = getPhrases(False)
# hyperparameters
lr = tf.constant(0.005, tf.float32)
batch_size = 100

# neural net parameters
# num of visible nodes must match input size or input size must be truncated
# size of hidden layer is expected number of outputs (which in this case is set of all possible notes
# there must be a weight vector for the cost of going between the edges
# there must be a bias vector for all layers
num_hidden = 128
time_steps = 16
num_input = time_steps * note_range
num_epochs = 200
activation_function = tf.nn.relu

x = tf.placeholder(tf.float32, shape=[None, num_input], name="x")
w = tf.Variable(tf.random_normal([num_input, num_hidden], 0.01), name="weight")
bh = tf.Variable(tf.zeros([1, num_hidden], tf.float32, name="bias_hidden"))
bv = tf.Variable(tf.zeros([1, num_input], tf.float32, name="bias_visible"))

def sample(probs):
  return tf.floor(probs + tf.random_uniform(tf.shape(probs),0,1))

def gibbs_sample(k):
  def gibbs_step(count, k, xk):
    hk = sample(activation_function(tf.matmul(xk, w) + bh))
    xk = sample(activation_function(tf.matmul(hk, tf.transpose(w) + bv)))
    return count+1, k, xk

  ct = tf.constant(0)
  [_, _, x_sample] = control_flow_ops.while_loop(lambda count, num_iter, *args:count < num_iter,  gibbs_step, [ct, tf.constant(k), x], back_prop=False)
  x_sample = tf.stop_gradient(x_sample)
  return x_sample

x_sample = gibbs_sample(1)
h = sample(activation_function(tf.matmul(x, w) + bh))
h_sample = sample(activation_function(tf.matmul(x_sample, w) + bh))


# so there's a bias layer for the visible level, hidden level
# as well as a weight layer for each level to the next
# timesteps is equivalent to how long the neural network can remember things

size_bt = tf.cast(tf.shape(x)[0], tf.float32)
w_adder = tf.multiply(lr / size_bt,
tf.subtract(tf.matmul(tf.transpose(x), h), tf.matmul(tf.transpose(x_sample), h_sample)))
bv_adder = tf.multiply(lr / size_bt, tf.reduce_sum(tf.subtract(x, x_sample), 0, True))
bh_adder = tf.multiply(lr / size_bt, tf.reduce_sum(tf.subtract(h, h_sample), 0, True))
updt = [w.assign_add(w_adder), bv.assign_add(bv_adder), bh.assign_add(bh_adder)]
with tf.Session() as sess:

  init = tf.global_variables_initializer()
  sess.run(init)
  #updt= contrastive_divergence(learning_rate)
  for epoch in tqdm(range(num_epochs)):
    for _classification, phrase in phrases:
    # A phrase is an array of integers which correspond to certain notes
      phrase = np.array(phrase)
      phrase = phrase[:int(np.floor(phrase.shape[0]/time_steps)* time_steps)]
      phrase = np.reshape(phrase, [int(phrase.shape[0]/time_steps), int(phrase.shape[1] * time_steps)])

      for i in range(1, len(phrase), batch_size):
        tr_x = phrase[i:i+batch_size]
        sess.run(updt, feed_dict={x: tr_x})

  NUM_SAMPLE_OUTPUTS = 20
  sample = gibbs_sample(1).eval(session = sess, feed_dict = {x: np.zeros((NUM_SAMPLE_OUTPUTS, num_input))})
  for i in range(sample.shape[0]):
    if not any(sample[i, :]):
      continue
    S = np.reshape(sample[i,:], (time_steps, note_range))
    print(S)
