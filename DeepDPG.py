import theano
from theano import tensor as T
import numpy as np
import lasagne

def sgd(cost, params, lr=0.05):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        updates.append([p, p + (-g * lr)])
    return updates

def rlTDSGD(cost, delta, params, lr=0.05):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        updates.append([p, p + (lr * delta * g)])
    return updates

# For debugging
# theano.config.mode='FAST_COMPILE'

class DeepDPG(object):
    
    def __init__(self, n_in, n_out):

        batch_size=32
        state_length=n_in
        action_length=n_out
        # data types for model
        State = T.dmatrix("State")
        State.tag.test_value = np.random.rand(batch_size,state_length)
        ResultState = T.dmatrix("ResultState")
        ResultState.tag.test_value = np.random.rand(batch_size,state_length)
        Reward = T.col("Reward")
        Reward.tag.test_value = np.random.rand(batch_size,1)
        Action = T.dmatrix("Action")
        Action.tag.test_value = np.random.rand(batch_size, action_length)
        # create a small convolutional neural network
        inputLayerActA = lasagne.layers.InputLayer((None, state_length), State)
        l_hid2ActA = lasagne.layers.DenseLayer(
                inputLayerActA, num_units=64,
                nonlinearity=lasagne.nonlinearities.leaky_rectify)
        
        l_hid3ActA = lasagne.layers.DenseLayer(
                l_hid2ActA, num_units=32,
                nonlinearity=lasagne.nonlinearities.leaky_rectify)
    
        self._l_outActA = lasagne.layers.DenseLayer(
                l_hid3ActA, num_units=n_out,
                nonlinearity=lasagne.nonlinearities.linear)
        
        inputLayerA = lasagne.layers.InputLayer((None, state_length), State)

        concatLayer = lasagne.layers.ConcatLayer([inputLayerA, self._l_outActA])
        l_hid2A = lasagne.layers.DenseLayer(
                concatLayer, num_units=64,
                nonlinearity=lasagne.nonlinearities.rectify)
        
        l_hid3A = lasagne.layers.DenseLayer(
                l_hid2A, num_units=32,
                nonlinearity=lasagne.nonlinearities.rectify)
    
        self._l_outA = lasagne.layers.DenseLayer(
                l_hid3A, num_units=1,
                nonlinearity=lasagne.nonlinearities.linear)
        # self._b_o = init_b_weights((n_out,))

        # self.updateTargetModel()
        inputLayerActB = lasagne.layers.InputLayer((None, state_length), State)
        l_hid2ActB = lasagne.layers.DenseLayer(
                inputLayerActB, num_units=64,
                nonlinearity=lasagne.nonlinearities.leaky_rectify)
    
        l_hid3ActB = lasagne.layers.DenseLayer(
                l_hid2ActB, num_units=32,
                nonlinearity=lasagne.nonlinearities.leaky_rectify)
        
        self._l_outActB = lasagne.layers.DenseLayer(
                l_hid3ActB, num_units=n_out,
                nonlinearity=lasagne.nonlinearities.linear)

        inputLayerB = lasagne.layers.InputLayer((None, state_length), State)
        concatLayerB = lasagne.layers.ConcatLayer([inputLayerB, self._l_outActB])
        l_hid2B = lasagne.layers.DenseLayer(
                concatLayerB, num_units=64,
                nonlinearity=lasagne.nonlinearities.rectify)
        
        l_hid3B = lasagne.layers.DenseLayer(
                l_hid2B, num_units=32,
                nonlinearity=lasagne.nonlinearities.rectify)
    
        self._l_outB = lasagne.layers.DenseLayer(
                l_hid3B, num_units=1,
                nonlinearity=lasagne.nonlinearities.linear)
            
        # print "Initial W " + str(self._w_o.get_value()) 
        
        self._learning_rate = 0.0001
        self._discount_factor= 0.8
        self._rho = 0.95
        self._rms_epsilon = 0.001
        
        self._weight_update_steps=5
        self._updates=0
        
        self._states_shared = theano.shared(
            np.zeros((batch_size, state_length),
                     dtype=theano.config.floatX))

        self._next_states_shared = theano.shared(
            np.zeros((batch_size, state_length),
                     dtype=theano.config.floatX))

        self._rewards_shared = theano.shared(
            np.zeros((batch_size, 1), dtype=theano.config.floatX),
            broadcastable=(False, True))

        self._actions_shared = theano.shared(
            np.zeros((batch_size, n_out), dtype=theano.config.floatX),
            )
        
        self._q_valsActA = lasagne.layers.get_output(self._l_outActA, State)
        self._q_valsActB = lasagne.layers.get_output(self._l_outActB, ResultState)
        self._q_valsActB2 = lasagne.layers.get_output(self._l_outActB, State)
        inputs_ = {
            State: self._states_shared,
            Action: self._q_valsActA,
        }
        self._q_valsA = lasagne.layers.get_output(self._l_outA, inputs_)
        inputs_ = {
            ResultState: self._next_states_shared,
            Action: self._q_valsActB,
        }
        self._q_valsB = lasagne.layers.get_output(self._l_outB, inputs_)
        
        
        self._q_func = self._q_valsA
        self._q_funcAct = self._q_valsActA
        # self._q_funcAct = theano.function(inputs=[State], outputs=self._q_valsActA, allow_input_downcast=True)
        
        target = (Reward + self._discount_factor * self._q_valsB)
        diff = target - self._q_valsA
        loss = 0.5 * diff ** 2 + (1e-4 * lasagne.regularization.regularize_network_params(
        self._l_outA, lasagne.regularization.l2))
        loss = T.mean(loss)
        
        params = lasagne.layers.helper.get_all_params(self._l_outA)
        actionParams = lasagne.layers.helper.get_all_params(self._l_outActA)
        givens_ = {
            State: self._states_shared,
            # ResultState: self._next_states_shared,
            Reward: self._rewards_shared,
            # Action: self._actions_shared,
        }
        actGivens = {
            State: self._states_shared,
            # ResultState: self._next_states_shared,
            # Reward: self._rewards_shared,
            Action: self._actions_shared,
        }
        
        # SGD update
        #updates_ = lasagne.updates.rmsprop(loss, params, self._learning_rate, self._rho,
        #                                    self._rms_epsilon)
        # TD update
        updates_ = lasagne.updates.rmsprop(T.mean(self._q_func) + (1e-6 * lasagne.regularization.regularize_network_params(
        self._l_outA, lasagne.regularization.l2)), params, 
                    self._learning_rate * -T.mean(diff), self._rho, self._rms_epsilon)
        
        
        # actDiff1 = (Action - self._q_valsActB) #TODO is this correct?
        # actDiff = (actDiff1 - (Action - self._q_valsActA))
        # actDiff = ((Action - self._q_valsActB2)) # Target network does not work well here?
        actDiff = ((Action - self._q_valsActA)) # Target network does not work well here?
        actLoss = 0.5 * actDiff ** 2 + (1e-4 * lasagne.regularization.regularize_network_params( self._l_outActA, lasagne.regularization.l2))
        actLoss = T.mean(actLoss)
        
        # actionUpdates = lasagne.updates.rmsprop(actLoss + 
        #    (1e-4 * lasagne.regularization.regularize_network_params(
        #        self._l_outActA, lasagne.regularization.l2)), actionParams, 
        #            self._learning_rate * 0.01 * (-actLoss), self._rho, self._rms_epsilon)
        
        actionUpdates = lasagne.updates.rmsprop(T.mean(self._q_funcAct) + 
          (1e-4 * lasagne.regularization.regularize_network_params(
              self._l_outActA, lasagne.regularization.l2)), actionParams, 
                  self._learning_rate * 0.1 * (-T.mean(actDiff)), self._rho, self._rms_epsilon)
        
        
        
        self._train = theano.function([], [loss, self._q_valsA], updates=updates_, givens=givens_)
        self._trainActor = theano.function([], [actLoss, self._q_valsActA], updates=actionUpdates, givens=actGivens)
        self._q_val = theano.function([], self._q_valsA,
                                       givens={State: self._states_shared})
        self._q_action = theano.function([], self._q_valsActA,
                                       givens={State: self._states_shared})
        inputs_ = [
                   State, 
                   Reward, 
                   # ResultState
                   ]
        self._bellman_error = theano.function(inputs=inputs_, outputs=diff, allow_input_downcast=True)
        # self._diffs = theano.function(input=[State])
        
    def updateTargetModel(self):
        # print "Updating target Model"
        """
            Target model updates
        """
        all_paramsA = lasagne.layers.helper.get_all_param_values(self._l_outA)
        all_paramsB = lasagne.layers.helper.get_all_param_values(self._l_outB)
        lerp_weight = 0.001 
        # print "param Values"
        all_params = []
        for paramsA, paramsB in zip(all_paramsA, all_paramsB):
            # print "paramsA: " + str(paramsA)
            # print "paramsB: " + str(paramsB)
            params = (lerp_weight * paramsA) + ((1.0 - lerp_weight) * paramsB)
            all_params.append(params)
        all_paramsActA = lasagne.layers.helper.get_all_param_values(self._l_outActA)
        all_paramsActB = lasagne.layers.helper.get_all_param_values(self._l_outActB)
        all_paramsAct = []
        for paramsA, paramsB in zip(all_paramsActA, all_paramsActB):
            # print "paramsA: " + str(paramsA)
            # print "paramsB: " + str(paramsB)
            params = (lerp_weight * paramsA) + ((1.0 - lerp_weight) * paramsB)
            all_paramsAct.append(params)
        lasagne.layers.helper.set_all_param_values(self._l_outB, all_params)
        lasagne.layers.helper.set_all_param_values(self._l_outActB, all_paramsAct) 
    
    def train(self, states, actions, rewards, result_states):
        self._states_shared.set_value(states)
        self._next_states_shared.set_value(result_states)
        self._actions_shared.set_value(actions)
        self._rewards_shared.set_value(rewards)
        # print "Performing Critic trainning update"
        if (( self._updates % self._weight_update_steps) == 0):
            self.updateTargetModel()
        self._updates += 1
        loss, _ = self._train()
        lossActor, _ = self._trainActor()
        # diff_ = self._bellman_error(states, rewards, result_states)
        # print "Diff"
        # print diff_
        return loss
    
    def predict(self, state):
        # states = np.zeros((self._batch_size, self._state_length), dtype=theano.config.floatX)
        # states[0, ...] = state
        self._states_shared.set_value(state)
        action_ = self._q_action()[0]
        return action_
    def q_value(self, state):
        # states = np.zeros((self._batch_size, self._state_length), dtype=theano.config.floatX)
        # states[0, ...] = state
        self._states_shared.set_value(state)
        return self._q_val()[0]
    def bellman_error(self, state, action, reward, result_state):
        # return self._bellman_error(state, reward, result_state)
        return self._bellman_error(state, reward)
