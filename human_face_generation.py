import numpy as np
import pandas as pd
import os
from tqdm import tqdm
from PIL import Image
from matplotlib import pyplot as plt
import time
import imageio
import shutil
from google.colab import drive
drive.mount('/content/drive', force_remount=True)
main_dir = f'/content/drive/MyDrive/sub/'

images = []
for image_file in tqdm(os.listdir(main_dir)[:10000]):
    image = Image.open(main_dir + image_file).crop((0, 20, 178, 198))
    image.thumbnail((128,128), Image.ANTIALIAS)
    images.append(np.uint8(image))

images = np.array(images) / 255

plt.figure(1, figsize=(10, 10))
for i in range(26):
    plt.subplot(6, 6, i+1)
    plt.imshow(images[i])
    plt.axis('off')
plt.show()

from keras import Input
from keras.layers import Dense, Reshape, LeakyReLU, Conv2D, Conv2DTranspose, Flatten, Dropout
from keras.models import Model
from keras.optimizers import RMSprop

def make_generator():
    gen_input = Input(shape=(32, )) # Latent Dimension is 32

    x = Dense(128 * 16 * 16)(gen_input)
    x = LeakyReLU()(x)
    x = Reshape((16, 16, 128))(x)

    x = Conv2D(256, 5, padding='same')(x)
    x = LeakyReLU()(x)

    # The next 3 layers perform upsampling.
    x = Conv2DTranspose(512, 4, strides=2, padding='same')(x)
    x = LeakyReLU()(x)

    x = Conv2DTranspose(256, 4, strides=2, padding='same')(x)
    x = LeakyReLU()(x)

    x = Conv2DTranspose(256, 4, strides=2, padding='same')(x)
    x = LeakyReLU()(x)


    x = Conv2D(3, 7, activation='tanh', padding='same')(x)

    generator = Model(gen_input, x)
    return generator

def make_discriminator():
    disc_input = Input(shape=(128, 128, 3))

    x = Conv2D(512, 4, strides=2)(disc_input)
    x = LeakyReLU()(x)

    x = Conv2D(512, 4, strides=2)(x)
    x = LeakyReLU()(x)

    x = Conv2D(512, 4, strides=2)(x)
    x = LeakyReLU()(x)

    x = Conv2D(512, 4, strides=2)(x)
    x = LeakyReLU()(x)

    x = Flatten()(x)
    x = Dropout(0.5)(x)

    x = Dense(1, activation='sigmoid')(x)
    discriminator = Model(disc_input, x)

    optimizer = RMSprop(
        learning_rate=.0003,
        clipvalue=1.0
    )

    discriminator.compile(
        optimizer=optimizer,
        loss='binary_crossentropy'
    )

    return discriminator



generator = make_generator()
discriminator = make_discriminator()
discriminator.trainable = False
gan_input = Input(shape=(32, ))
gan_output = discriminator(generator(gan_input))
gan = Model(gan_input, gan_output)

optimizer = RMSprop(learning_rate=.0003, clipvalue=1.0)
gan.compile(optimizer=optimizer, loss='binary_crossentropy')

directory = '/content/drive/MyDrive/results'
file = '%s/generated_%d.png'
if not os.path.isdir(directory):
    os.mkdir(directory)

save_vector = np.random.normal(size=(32, )) / 2

start = 0
disc_losses = []
adv_losses = []
images_saved = 0
for step in range(2000):
    start_time = time.time()
    latent_vectors = np.random.normal(size=(20, 32))
    generated = generator.predict(latent_vectors)

    real = images[start:(start + 20)]
    combined_images = np.concatenate([generated, real])

    labels = np.concatenate([np.ones((20, 1)), np.zeros((20, 1))])
    labels += .05 * np.random.random(labels.shape)

    disc_loss = discriminator.train_on_batch(combined_images, labels)
    disc_losses.append(disc_loss)

    latent_vectors = np.random.normal(size=(20, 32))
    fake_targets = np.zeros((20, 1))

    adv_loss = gan.train_on_batch(latent_vectors, fake_targets)
    adv_losses.append(adv_loss)

    start += 20
    if start > images.shape[0] - 20:
        start = 0

    if step % 50 == 49:
        gan.save_weights('/content/drive/MyDrive/gan.h5')

        print('%d/%d: disc_loss: %.4f, adv_loss: %.4f.  (%.1f sec)' % (step + 1, 1000, disc_loss, adv_loss, time.time() - start_time))
        save_image = generator.predict(save_vector)
        im = Image.fromarray(np.uint8(save_image * 255))
        im.save(file % (directory, images_saved))
        images_saved += 1


plt.figure(1, figsize=(12, 8))
plt.subplot(125)
plt.plot(disc_losses)
plt.xlabel('epochs')
plt.ylabel('discriminant loss')
plt.subplot(125)
plt.plot(adv_losses)
plt.xlabel('epochs')
plt.ylabel('adversary loss')
plt.show()

images_to_gif = []
for filename in os.listdir(directory):
    images_to_gif.append(imageio.imread(directory + '/' + filename))
imageio.mimsave('/content/drive/MyDrive/visual.gif', images_to_gif)
shutil.rmtree(directory)
