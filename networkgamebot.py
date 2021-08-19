#!/usr/bin/env python3

import re
import discord
import config
import random
import igraph as ig


fig_fn = './network_game/curr_graph'
#EDGELIST = './network_game/test_edgelist.csv'
EDGELIST = './network_game/edgelist.csv'

class NetworkGameBot(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}! Ready for the network game!')

    async def on_message(self, message, voice_channel = 'class-sessions'):
        if message.author == self.user:
            return

        if (message.content.startswith('$network game')) and ('Teachers' in [r.name for r in message.author.roles]):
            print("Starting the game")
            classroom = [x for x in message.guild.members if x.status==discord.Status.online and not x.bot]

            present_students = []
            for member in classroom:
                if 'Students' in [r.name for r in member.roles]:
                    present_students.append(member)

            self.game_state = get_game_state(present_students, edgelist = EDGELIST)
            # Build a mapping from names to user objects so that people can refer to users
            if self.game_state is not None:
                self.active_list = {x.name: x for x in self.game_state}
                self.observers = [x for x in classroom if x not in self.game_state]
                for student in self.game_state:
                    await student.send(self.make_status(student, welcome = True))
                graphs = make_graph(self.game_state)
                for o in self.observers:
                    await o.send(self.get_observer_welcome())
                    for i, f in enumerate(graphs):
                        await message.author.send(f'Group {i+1}')
                        await o.send(file=discord.File(f))
            else:
                await message.channel.send("Not enough students to play")

        if message.content.startswith('$give'):
            try:
                msg_list = message.content.split(' ')
                u_to = ' '.join(msg_list[1:-1])
                resource = msg_list[-1]
                u_to = u_to.strip('@')
            except:
                await message.author.send("Badly formed command. It has to be '$give user resource'")
            if u_to not in self.active_list:
                await message.author.send(f"I can't find {u_to} in the list of users. Make sure the command is formatted as $give user resource")
            else:
                u_to = self.active_list[u_to]
                gave_resource = self.give_resource(resource, message.author, u_to)
                if gave_resource == True:
                    newly_finished = self.newly_finished(u_to)
                    await message.author.send(f"{resource} sent to {u_to.name}")
                    await message.author.send(f"You now have {self.game_state[message.author]['has']} and you need {self.game_state[message.author]['needs']}")
                    if newly_finished:
                        await u_to.send("You have everything you need! Well done! You can keep passing resources and talking with your 'neighbors' if you like. Just make sure to keep the resources that you need!")
                    else:
                        await u_to.send(f"You now have {self.game_state[u_to]['has']} and you need {self.game_state[u_to]['needs']}")
                    # Also send updates to observers
                    for o in self.observers:
                        await o.send(f"{message.author.name} sent {resource} to {u_to.name}")
                        if newly_finished:
                            await o.send(f"{u_to.name} has everything they need!!!")

                else:
                    await message.author.send(f"Resource not sent. Are you sure you have {resource} and that you can give it to {u_to.name}?")


        if message.content.startswith('$status'):
            if message.author in self.game_state:
                await message.author.send(self.make_status(message.author))
            elif message.author in self.observers:
                graphs = make_graph(self.game_state)
                for i, f in enumerate(graphs):
                    await message.author.send(f'Group {i+1}')
                    await message.author.send(file=discord.File(f))
            else:
                await message.author.send("I couldn't find you. Are you playing the game?")



    def newly_finished(self, u_to):
        u_data = self.game_state[u_to]
        if set(u_data['needs']) <= set(u_data['has']):
            # Check if already finished from before
            if u_data['finished'] == True:
                return False
            else:
                u_data['finished'] = True
                return True
        u_data['finished'] = False
        return False

    def make_status(self, student, welcome = False):
        s = ''
        if welcome == True:
            s += '''
Welcome to the Network Game!
The goal of the game is to get the resources you need as quickly as possible.

Rules:
1. All communication has to be one-to-one (i.e., via DM on Discord) and only with your neighbors
2. All communication has to be written, but you can write whatever you want


'''
        s += 'You are allowed to communicate with:\n'
        for neighbor in self.game_state[student]['neighbors']:
            s += f"{neighbor.mention}\n"
        s += f"You have these resources: {self.game_state[student]['has']}.\n"
        s += f"You need: {self.game_state[student]['needs']}."
        if welcome == True:
            s += '''

You can give resources to others by talking to me. For example, to give A to JeremyFoote you would type

$give JeremyFoote A.

If you forget what resources you have or who your neighbors are, just type this in a message to me:

$status
'''
        return s


    def give_resource(self, resource, u_from, u_to):
        if resource not in self.game_state[u_from]['has']:
            return False
        if u_to not in self.game_state[u_from]['neighbors']:
            return False
        else:
            self.game_state[u_from]['has'].remove(resource)
            self.game_state[u_to]['has'].append(resource)
            return True

    def get_observer_welcome(self):
        s = '''
Welcome to the Network Game!

You are an observer this round. This is admittedly not as fun as playing the game, but I've tried to make it as exciting as possible.

Everyone who is playing exists as part of a network. They have resoures, and they are trying to get different resources. Right after this message you should see one or two network graphs. These give you a birds-eye view of everyone who is playing the game. They show how everyone who is playing is connected, what they have, and what they need.

The cool thing about these graphs is that they will be updated as people play the game. You can call them up by typing a message to me that simply says:

$status

You will also get a message any time someone gives a resource to someone else.'''

        return s


def get_game_state(student_list,
        edgelist,
        resource_prefix = './network_game/resources_'
        ):


    def _add_connection(node1, node2):
        node1 = int(node1)
        node2 = int(node2)
        for i in range(len(mapping[node1])):
            s1 = mapping[node1][i]
            s2 = mapping[node2][i]
            if s1 in game_state:
                game_state[s1]['neighbors'].append(s2)
            else:
                game_state[s1] = {'neighbors': [s2]}

    def _add_resources():
        fn = f"{resource_prefix}{group_size}.csv"
        with open(fn, 'r') as f:
            i = 1
            for line in f.readlines():
                resources = line.strip().split(',')
                curr_students = mapping[i]
                for s in curr_students:
                    game_state[s]['has'] = resources[:3]
                    game_state[s]['needs'] = resources[3:]
                    game_state[s]['finished'] = False
                i += 1



    game_state = {}
    group_size = _get_group_size(len(student_list))
    if len(student_list) < group_size:
        return None
    mapping = _make_mapping(student_list, group_size)
    with open(edgelist, 'r') as f:
        for line in f.readlines():
            node1, node2 = line.strip().split(',')
            if int(node2) <= group_size:
                _add_connection(node1, node2)
                _add_connection(node2, node1)
    _add_resources()
    #return (game_state, len(student_list)//group_size)
    return game_state



def _make_mapping(students, group_size):
    random.shuffle(students)
    n_observers = len(students) % group_size
    mapping = {}
    if n_observers > 0:
        mapping['observers'] = students[-n_observers:]
        students = students[:-n_observers]
    for i, student in enumerate(students):
        j = i % group_size
        idx = j + 1
        if idx in mapping:
            mapping[idx].append(student)
        else:
            mapping[idx] = [student]

    return mapping


def _get_group_size(n,
        min_size = 7,
        max_size = 9):
    min_observers = None
    for x in range(min_size, max_size + 1):
        observers = n % x
        if min_observers is None or observers < min_observers:
            best_fit = x
            min_observers = observers
    return best_fit


def make_graph(game_state):
    labels = []
    colors = []
    G = ig.Graph()
    G.add_vertices([x.name for x in game_state])
    for student, vals in game_state.items():
        colors.append('gold' if vals['finished'] == True else 'lightblue')
        labels.append(f'''{student.name}
            Has: {vals['has']}
            Needs: {vals['needs']}''')
        for neighbor in vals['neighbors']:
            G.add_edge(student.name, neighbor.name)
    G.vs['label'] = labels
    G.vs['color'] = colors
    G = G.as_undirected()
    i = 1
    graph_fns = []
    for nodes in G.components():
        sg = G.subgraph(nodes)
        fn = f'{fig_fn}_{i}.png'
        plot = ig.plot(sg.simplify(), margin = 80, target = fn)
        graph_fns.append(fn)
        i += 1
    return graph_fns



def main():
    # this is necessary to get information about who is online
    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True

    gamebot = NetworkGameBot(intents=intents)
    gamebot.run(config.netgamekey)


if __name__ == '__main__':
    main()
