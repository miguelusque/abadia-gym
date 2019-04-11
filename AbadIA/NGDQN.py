import random
import numpy as np
import logging
import json
from math import hypot
from math import atan2

from keras.models import Sequential, load_model
from keras.layers import Dense, Dropout
from keras.optimizers import Adam
from collections import deque

# TODO JT:
# 1) Need a method to fill the memory with actions
# 2) Need a method to training / validating out the agent
# 3) A method to get the history of the training/validating
# 4) a method to convert from the json format to the input vector

class NGDQN:
    def __init__(self, env=None, modelName=None, initModelName=None, gsBucket=None):
        self.env     = env
        self.memory  = deque(maxlen=10000)
        # Exploring or playing

        self.gamma = 0.85
        self.epsilon = 1.0
        self.epsilon_min = 0.01 # previously 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.005
        self.tau = .125
        self.initModelName = None
        self.modelName = None
        self.gsBucket = None

        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%d-%m-%y %H:%M:%S',
                            level=logging.INFO)

        self.logging = logging

        # TODO JT: we need to implement this when goes to production
        # if env != None:
        if modelName == None and initModelName == None:
            self.model        = self.create_model()
            self.target_model = self.create_model()
        else:
            self.initModelName = initModelName
            self.modelName = modelName

            # initModelName will have priority over modelName on load if both are defined.
            # on the save operation will use modelName
            # with this we can load a model and save into a different file name

            if (initModelName is not None):
                fileName = initModelName
            else:
                fileName = modelName

            if (self.gsBucket != None):
                # TODO JT: we need to implement this when goes to production
                if self.env != None:
                    self.env.download_blob(fileName, fileName)
                self.logging.info("Downloading the model from Bucket: {} file: {}".format(self.gsBucket, fileName))

            self.model        = self.load_model(fileName)
            self.target_model = self.load_model(fileName)
    def create_model(self, input_dim=71, output_dim=9):
        self.logging.info("Creating a new model v6")
        model   = Sequential()
        # TODO JT we need to increment the input vector dim
        # for now the input_dim is 71 with chars, env + validmods

        state_shape  = input_dim # self.env.observation_space.shape

        # TODO JT we need to redesign the internal lawyers

        model.add(Dense(64, input_shape=(1,71), activation="relu"))
        model.add(Dense(128, activation="relu"))
        model.add(Dense(64, activation="relu"))
        model.add(Dense(32, activation="relu"))
        model.add(Dense(output_dim))
        model.compile(loss="mean_squared_error",
            optimizer=Adam(lr=self.learning_rate))
        return model


    def create_model2(self, input_dim=71, output_dim=9):
        self.logging.info("Creating a new model2 v6")
        model   = Sequential()
        # TODO JT we need to increment the input vector dim
        # for now the input_dim is 71 with chars, env + validmods

        state_shape  = input_dim # self.env.observation_space.shape

        # TODO JT we need to redesign the internal lawyers

        model.add(Dense(64, input_shape=(1,71), activation="relu"))
        model.add(Dense(128, activation="relu"))
        model.add(Dense(64, activation="relu"))
        model.add(Dense(32, activation="relu"))
        model.add(Dense(output_dim))
        model.compile(loss="mean_squared_error",
            optimizer=Adam(lr=self.learning_rate))
        return model

    def load_model(self, name):
        self.logging.info("Loading a local model from: ({})".format(name))
        # TODO JT: is that right?????
        return load_model(name)

    def create_empty(self, name="models/model_v6"):
        model = self.create_model()
        self.save_model(name)
        return model

    def act(self, vector):
        self.epsilon *= self.epsilon_decay
        self.epsilon = max(self.epsilon_min, self.epsilon)
        if (self.env == None):
            return act_prediction(vector)
        else:
            return act_env(vector)

    def act_prediction(self, vector):

        # self.env.vector = vector

        predictions = self.model.predict(vector)[0]
        # self.env.predictions = predictions
        # TODO JT: how to get the action_space
        # final = np.zeros(self.env.action_space.n)

        action = np.argmax(final)
        self.logging.info("vector:      {}              ".format(vector))
        self.logging.info("predictions: {}              ".format(predictions))
        self.logging.info("final:       {}              ".format(final))
        self.logging.info("Action:      {} Prediction: {}    ".format(action, final[action]))

        return action

    def act_env(self, vector):

        vector = self.env.stateVector()
        self.env.vector = vector

        if (self.env.playing is False) and (np.random.random() < self.epsilon):
            action = self.env.action_space.sample()
            self.env.logging.info("e-greedy: {}  epsilon: {}<----               ".format(action, self.epsilon))
            actionType = "E"
            self.env.calculated_predictions = []
            self.env.final_predictions = []
        else:
            predictions = self.model.predict(vector)[0]
            self.env.predictions = predictions
            final = np.zeros(self.env.action_space.n)

            for ii in range(0,self.env.action_space.n):
                if (self.env.valMovs[ii] >= 1):
                    final[ii] = predictions[ii]
                else:
                    final[ii] = -99 # predictions[ii]*0.9

            action = np.argmax(final)
            self.env.logging.info("vector:      {}              ".format(vector))
            self.env.logging.info("predictions: {}              ".format(predictions))
            self.env.logging.info("final:       {}              ".format(final))
            self.env.logging.info("Action:      {} Prediction: {}    ".format(action, final[action]))
            actionType = "P"

            self.env.calculated_predictions = predictions.tolist()
            self.env.final_predictions = final.tolist()


        self.env.vector_predictions = vector.tolist()
        self.env.action_predictions = int(action)
        self.env.action_type = actionType

        return action

    def remember(self, state, action, reward, new_state, done):
        self.memory.append([state, action, reward, new_state, done, 0])

    def replay(self, verbose=0):
        batch_size = 32
        if len(self.memory) < batch_size:
            return

        temp = self.memory
        acu  = np.zeros(32)

        # adding the future reward 32 rewards ahead to the vector information
        for index in range(len(temp)-1, 0, -1):
            acu[index % 32] = temp[index][2]
            temp[index][5]  = acu.sum()

        samples = random.sample(temp, batch_size)
        for sample in samples:
            state, action, reward, new_state, done, future_reward = sample
            target = self.target_model.predict(state)
            if done:
                target[0][action] = future_reward
            else:
                Q_future = max(self.target_model.predict(new_state)[0])
                target[0][action] = future_reward # Q_future # reward + Q_future * self.gamma
            history = self.model.fit(state, target, epochs=1, verbose=verbose)
            # print("loss:", history.history["loss"], "\n")

    def replay_game(self, epochs=4, verbose=0):
        batch_size = 32
        if len(self.memory) < batch_size:
            return

        temp = self.memory
        acu  = np.zeros(32)

        # adding the future reward 32 rewards ahead to the vector information
        for index in range(len(temp)-1, 0, -1):
            acu[index % 32] = temp[index][2]
            temp[index][5]  = acu.sum()

        # samples = random.sample(temp, batch_size)
        # TODO JT: we dont want to use the last 32 actions because we dont have the "future" score

        states  = []
        rewards = []
        for sample in temp:
            state, action, reward, new_state, done, future_reward = sample
            target = self.target_model.predict(state.reshape(1,1,71))
            # TODO JT: we need to fix this for the case done is True
            if done:
                target[0][0][action] = future_reward
            else:
                target[0][0][action] = future_reward
            states.append(state)
            rewards.append(target)

        X_training = np.array(states).reshape(len(states), 1, 71)
        Y_training = np.array(rewards).reshape(len(rewards), 1, 9)
        history = self.model.fit(X_training, Y_training, epochs=epochs, batch_size=32, verbose=verbose)

        print("loss:", history.history["loss"], "\n")
        return history

    def target_train(self):
        self.env.logging.info("training target ..")
        weights = self.model.get_weights()
        target_weights = self.target_model.get_weights()
        for i in range(len(target_weights)):
            target_weights[i] = weights[i] * self.tau + target_weights[i] * (1 - self.tau)
        self.target_model.set_weights(target_weights)

    def save_model(self, fn):
        self.logging.info("Saving the model to the local file: {}".format(fn))
        self.model.save(fn)

    def load_actions_from_a_file(self, fileName):
        self.memory = deque(maxlen=10000)
        with open(fileName) as json_data:
            # TODO JT: we need to optimize this reading a line by a line
            lines = json_data.readlines()
            if lines:
                for line in lines:
                    # if (len(line) > 0 and line.startswith("[")):
                    state = json.loads(line)[0]
                    # print("{}".format(state))

                    current_state = self.state2vector(state['action']['state'])
                    new_state = self.state2vector(state['action']['state'])
                    action = state['action']['action']
                    reward = state['action']['reward']

                    self.remember(current_state, action, reward, new_state, False)

    def state2vector(self, state):

        chars  = state['Personajes']
        # print(chars)
        vChars = np.zeros([4,7], np.float)
        for ii in range(0, min(len(chars), 4)):
            # print (ii, chars[ii]['nombre'], chars[ii]['posX'], chars[ii]['posY'])
            vChars[ii][0] = float(chars[ii]['posX']/256)
            vChars[ii][1] = float(chars[ii]['posY']/256)
            vChars[ii][2] = float(chars[ii]['orientacion'] / 4)
            vChars[ii][3] = float(chars[ii]['altura'] / 4)
            if (ii >= 1):
                vChars[ii][4] = hypot(vChars[ii][0] - vChars[0][0], vChars[ii][1] - vChars[0][1])
                vChars[ii][5] = atan2(vChars[ii][0] - vChars[0][0], vChars[ii][1] - vChars[0][1]) / 3.14159
            if (ii <= 1):
                vChars[ii][6] = float(chars[ii]['objetos'] / 32)

        # vEnv vector with the environment data
        vEnv = np.zeros([10], np.float)
        vEnv[0] = float(state['bonus']/100)
        vEnv[1] = float(state['dia']/7)
        vEnv[2] = float(state['momentoDia']/10)
        vEnv[3] = float(state['numPantalla']/256)
        vEnv[4] = float(state['numeroRomano']/10)
        vEnv[5] = float(state['obsequium']/31)
        vEnv[6] = float(state['planta']/3)
        vEnv[7] = float(state['porcentaje']/100)
        if len(state['Objetos']) >= 1:
            vEnv[8] = float(state['Objetos'][0]/32)

        if 'jugada' in state:
            vEnv[9] = float(state['jugada']/10000)

        # print(vEnv)
        vector = np.append(vChars.reshape([1, 28]), vEnv)

        # vAudio the last sounds
        vAudio = np.zeros([12], np.float)
        for ii in range(0, len(state['sonidos'])):
            vAudio[ii] = float(state['sonidos'][ii]/64)

        vector = np.append(vector, vAudio)

        # vFrases the last frases
        vFrases = np.zeros([12], np.float)
        for ii in range(0, len(state['frases'])):
            vFrases[ii] = float(state['frases'][ii]/64)

        vector = np.append(vector, vFrases)

        # vValidm the validmovs
        vValidm = np.zeros([9], np.float)
        if 'valMovs' in state and state['valMovs'] != None:
            for ii in range(len(state['valMovs'])):
                vValidm[ii] = float(state['valMovs'][ii])

        vector = np.append(vector, vValidm)

        # print("vector {}".format(vector))
        return vector.reshape(1,71)

