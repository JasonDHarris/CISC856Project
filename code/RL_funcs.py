import numpy as np
import random

def reward_function(col_probs):
    rwd = np.sum(-1*col_probs)
    return rwd

def generate_actions(action_space, num_actions):
    actions = np.empty([1,num_actions])
    for i in range(num_actions):
        action = random.choices(action_space)
        actions[i] = action
    return actions

def best_actions(action_sets, rwds):
    best = np.argmax(rwds)
    action = action_sets[best]
    return action

def future_prob_of_colision(y):
    b = np.mean(y)
    # bs = []
    # for y_hat in y_hats:
    #     b = np.mean(y_hat)
    #     bs.append(b)
    # b = np.min(bs)
    return b
