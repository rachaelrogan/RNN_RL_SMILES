import tensorflow as tf
g = tf.Graph()
with g.as_default() as g:
    tf.train.import_meta_graph('./data/tf_model_acceptor_smi_tuneall2.ckpt')
with tf.Session(graph=g) as sess:
    file_writer = tf.summary.FileWriter(logdir='./results',graph=g)