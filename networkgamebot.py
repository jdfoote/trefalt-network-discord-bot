#!/usr/bin/env python3

import re
import discord
import config
import random
import igraph as ig


fig_fn = './network_game/curr_graph'

class NetworkGameBot(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}! Ready for the network game!')

    async def on_message(self, message, voice_channel = 'Class Sessions'):
        if message.author == self.user:
            return

        # TODO: Only let admin send this command
        if (message.content.startswith('$network game')) and ('Teachers' in [r.name for r in message.author.roles]):
            print("Starting the game")
            classroom = [x for x in message.guild.voice_channels if x.name == voice_channel and x.category_id == message.channel.category_id][0]

            present_students = []
            for member in classroom.members:
                if 'Students' in [r.name for r in member.roles]:
                    present_students.append(member)

            self.game_state = get_game_state(present_students, edgelist = './network_game/test_edgelist.csv')
            # Build a mapping from names to user objects so that people can refer to users
            self.active_list = {x.name: x for x in self.game_state}
            self.observers = [x for x in classroom.members if x not in self.game_state]
            if self.game_state is not None:
                for student in self.game_state:
                    await student.send(self.make_status(student))
                graphs = make_graph(self.game_state)
                for o in self.observers:
                    for f in graphs:
                        await o.send(file=discord.File(f))
            else:
                for student in present_students:
                    await student.send("Not enough students to play")

        if message.content.startswith('$give'):
            try:
                _, u_to, resource = message.content.split(' ')
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
                for f in graphs:
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

    def make_status(self, student):
        str = 'You are allowed to talk to:\n'
        for neighbor in self.game_state[student]['neighbors']:
            str += f"{neighbor.mention}\n"
        str += f"You have these resources: {self.game_state[student]['has']}.\n"
        str += f"You need: {self.game_state[student]['needs']}."
        return str


    def give_resource(self, resource, u_from, u_to):
        if resource not in self.game_state[u_from]['has']:
            return False
        if u_to not in self.game_state[u_from]['neighbors']:
            return False
        else:
            self.game_state[u_from]['has'].remove(resource)
            self.game_state[u_to]['has'].append(resource)
            return True


def get_game_state(student_list,
        edgelist = './network_game/edgelist.csv',
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
    for i, student in enumerate(students[-n_observers:]):
        j = i % group_size
        idx = j + 1
        if idx in mapping:
            mapping[idx].append(student)
        else:
            mapping[idx] = [student]
    return mapping


def _get_group_size(n):
    min_observers = None
    for x in range(7,10):
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
        plot = ig.plot(sg, margin = 80, target = fn)
        graph_fns.append(fn)
        i += 1
    return graph_fns



# this is necessary to get information about who is online
intents = discord.Intents.default()
intents.members = True
intents.presences = True

gamebot = NetworkGameBot(intents=intents)
gamebot.run(config.netgamekey)
