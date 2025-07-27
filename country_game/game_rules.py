"""
Country Game Rules Module

This module contains the rules for the Country Game as docstrings.
The rules are organized into sections, with each section represented by a function.
The docstring of each function contains the content for that section.
"""

def get_all_sections():
    """
    Returns a dictionary containing all sections of the game rules.
    Each key is a section title, and each value is a list of lines for that section.
    """
    sections = {}

    # Add each section to the dictionary
    sections["Introduction"] = get_introduction.__doc__.strip().split('\n')
    sections["Country Achievements"] = get_country_achievements.__doc__.strip().split('\n')
    sections["What to Expect"] = get_what_to_expect.__doc__.strip().split('\n')
    sections["Actions, What They're Made of, How to Submit Them, Resolution, and More"] = get_actions.__doc__.strip().split('\n')
    sections["Action-less Actions aka Free Actions"] = get_free_actions.__doc__.strip().split('\n')
    sections["Tips"] = get_tips.__doc__.strip().split('\n')

    # Clean up the sections (remove empty lines at the beginning)
    for section_name, lines in sections.items():
        while lines and not lines[0].strip():
            lines.pop(0)

    return sections

def get_introduction():
    """
This is the 5th edition of the Country Game. The Country Game is a roleplaying game wherein players take on the role of leaders of fantastical nations in a fantastical world. Gameplay officially occurs over email, Discord, World Anvil, and Google Drive although players are welcome to discuss or roleplay outside of these mediums as well. There are more than 30 pre-generated nations just waiting for someone to lead them into legend.    

The Country Game is inspired by, and indeed runs off of, the realities of physics as presented in the Pathfinder RPG. This isn't to say that the countries use those game mechanics, and you won't be using them to accomplish your goals in the game, but frequently the staff will be describing game elements in terms, creatures, and magic from the Pathfinder RPG.  

Updates from Previous Editions: In the 5th age the god king has increased his divine rank from that of a demigod to a full deity. The elven mithal was shattered after the elven king went insane. He was put down by the new ruler, but the damage had already been done. Morgaard - Either the paladin has put down the lich king/queen OR the lich king/queen has put down the paladin and declared rule with an iron fist. There is a new pope! New policies will come from the Pope soon. A new nation was contacted out in the seas. The merfolk remain elusive, but could grow into a mighty power.

Actions must be submitted through the character portal, a spreadsheet-style file that has been shared with each player. You can contact us via country.game.05@gmail.com or discord. On Mondays you may come and talk to a storyteller, time TBD, appointments are also possible. In person meetings with the staff are on hold during the Covid-19 pandemic

***DISCLAIMER*** Player information is not absolute, and is limited to the means available in the game to receive it. For example, it is entirely possible that a neighboring country with an Espionage of 5 might know more about what's happening in your country than you do. Also, this document does not include all possibilities of gameplay. Just because you don't see something spelled out here doesn't mean it is out of the scope of the game. ***DISCLAIMER***

The Country Game is a storyteller arbitration game first and foremost. What rules are written are guidelines to serve as shorthand to help the staff remember or adjudicate.

Notes to reading this guide: 
1. The strictures here apply to countries in general, but specific countries may have exceptions. Exceptions will be specified on the country's sheet. So please keep this in mind.
2. There are some hard rules, which apply to everyone. In general if you read a rule, that rule is the one that applies. If there is confusion between two rules, the prevailing rule is this: Specific beats general.
    """
    return

def get_country_achievements():
    """
Players are encouraged to come up with personal goals for what they would like to get out of playing the Country Game, but we will also provide some ideas for each country. Each country will receive three goals personalized for that country. You the player have no obligation to pursue them, but we hope you will at least find them inspiring. Achieving a country goal does not end the game, but does grant bragging rights as they tend to be rather challenging. These goals are also meant to be an indication of what your own nation and others will expect from you as the ruler. You should note that significant progress toward your nation's goals will also have a positive effect on your Trust statistic.
    """
    return

def get_what_to_expect():
    """
From the World
Time: Each 2 real life weeks is one season in game. Every four seasons in game is one year. So, one in-game year is 4 seasons or 4 turns (or 8 weeks) out of game. 
* Winter: Invasions are more challenging due to the cold, especially in more northern climates. Players must engage a project that will store food for the winter.
* Spring: Projects are more difficult to accomplish due to planting and rains, a typical surcharge of 1F or 1g. Flooding is more common
* Summer: Invasions are more challenging due to extreme heat, especially in the south. Summer storms may disrupt trade.
* Fall: Many crops produce extra food. This is treated as a (g) bonus in the form of taxation, plentiful spending, etc.

Events: Each year at least one large regional event will happen somewhere on the continent. Some events will be tied to the seasons specifically, such as Harsh Winter: Due to extreme cold, snow, and spirits of hunger, every player must complete a project called "Winter Stores." (Generally a Size + Economy project that gets bonuses with food.) There is also a greater chance of undead rising. Affects northern countries more than southern. Other events may be the result of cosmic forces or player actions.

From Other Players
Other players' actions may affect your country. Other players' actions may affect what information you have. We also expect our players to be courteous out of character and keep in-character and out-of-character conflicts separate. This is a game, played for fun. It is expected that players will behave compassionately towards their fellow players. This means that they will act to make other players' games better. If a player behaves in a way that deliberately harms and discomforts other players, that player will be asked to leave.

From the Staff
Players can expect courteous responses from staff. The staff will maintain a strict in-character vs out-of-character separation. The staff will provide information on and run independent (NPC) nations. Staff will try to respond to questions within 24 hours. If we do not please be patient and ask again. Please let us know if you have any concerns.
    """
    return

def get_actions():
    """
Actions are the meat and potatoes of gameplay, they represent time, effort, and political wrangling on the part of the player (or NPCs). Actions are how you materially affect your country and the countries of other players. Each player gets 3-5 actions (see your country sheet) and the NPCs of each nation gets 0-2 collective actions. The NPC actions are not taken by your advisors, it is taken by other factors or groups within your nation. If the player does not declare their actions then those are taken by their advisors. An action consists of a description of the desired outcome, how it will be accomplished, and what resources are being applied.  

Submitting Actions
Actions need to be submitted via the player portal (that Google Sheet thing) every other Friday by 11:59 PM in order to be processed for the upcoming turn beginning on Sunday. 1 turn = 2 weeks out of game and 1 season in game. It is requested that actions be ordered by their priority so that the staff can ensure that the things you think are most important are treated that way. Staff will then get together and suss out what happens.

Sample Actions
There are effectively an infinite number of different actions players can submit, but here are a few examples of some we think will come up:
* Mobilizing a battlegroup to invade another country (required pre-invasion)
* Growing your infrastructure
* Urban development, settling a new town or growing a town into a city.
* Establishing a new trade route
* Establishing a spy network
* Calling on local clerics to treat victims of a plague
* Exploiting a resource to get an extra unit of it for some turns.
* Raiding/piracy - smaller groups, faster movement, no territory taken
* Spreading/collecting information
* Searching/prospecting for natural resources.
* Assimilating a hex
    """
    return

def get_free_actions():
    """
Some actions don't actually take up one of your actions, but you do need to submit in writing that you're doing it. These are action-less actions, or more succinctly, free actions.  
* Converting copper, silver, and gold into currency
* Using towns and cities to sell resources for currency within your nation
* Hiring adventures to solve a problem
* One time trade
    """
    return

def get_tips():
    """
The below are some tips and guidelines for submitting effective actions.  
* Your stats represent a finite pool of personnel, knowledge, and equipment. Try not to rely too heavily on actions that seem like they would all use a single statistic for your nation (ie. they shouldn't all be military actions, or trade actions, and so on.) Try to balance spreading out the sorts of actions you take with playing to your strengths. You may use a single stat only twice per turn for an action.
* If you have a relevant advisor to an action please include it, we will try to remember, but reminders are definitely helpful.
* Throwing money at a problem always helps. 

Amount of Money (g) Added to the Action | Bonus
1 | +1
3 | +2
6 | +3
10 | +4
15 | +5

* Supplying food to people engaging in difficult tasks basically always helps, and is mandatory for any project that involves deploying significant numbers of people.
* Include relevant resources. In most cases resources are mandatory. For example if you want to build a ship, include some kind of wood, either as a special resource or pulling off of forest tiles in your nation.
* Explaining your reasoning for why you think an idea should work; this helps us understand where you're coming from, which in turn lets us put your actions in a framework that's far more likely to succeed.
* You can spend another action to assist an action your taking. This second action can use any stats you can justify and will add ½ it's rollovers as a bonus on the action. This bonus can last for multiple turns. An example is using espionage to boost your battlegroup with enemy intel
    """
    return

def get_suggestions():
    """
    Returns a list of suggested improvements based on the game rules.
    """
    return [
        {
            'title': 'Implement Free Actions',
            'description': 'The rules mention "free actions" that don\'t consume action slots. Consider adding a checkbox to the actions form to mark an action as "free".',
            'rule_reference': 'Action-less Actions aka Free Actions',
            'implementation_hint': 'Add a boolean field to the actions table and update the form in actions.html.'
        },
        {
            'title': 'Add Seasonal Effects',
            'description': 'The game has seasonal effects that impact gameplay. Consider adding season tracking and applying seasonal modifiers to actions and projects.',
            'rule_reference': 'Time: Each 2 real life weeks is one season in game.',
            'implementation_hint': 'Add a seasons table and update the action resolution logic to account for seasonal effects.'
        },
        {
            'title': 'Calculate Action Bonuses',
            'description': 'Gold spent on actions provides specific bonuses. Consider automatically calculating and displaying these bonuses.',
            'rule_reference': 'Throwing money at a problem always helps.',
            'implementation_hint': 'Update the action form to show the calculated bonus based on gold spent.'
        },
        {
            'title': 'Implement Country Achievements',
            'description': 'Each country has personalized goals. Consider adding a system to track progress toward these goals.',
            'rule_reference': 'Country Achievements',
            'implementation_hint': 'Add an achievements table and UI for tracking progress.'
        }
    ]
