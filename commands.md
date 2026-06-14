# 🎲 Without Number Bot - Command List

DICEwithoutNumber is a free, open-source, accessibility-focused Discord bot for Without Number games and other tabletop RPGs. It provides voice-friendly commands, multilingual tools, character sheets, rules references, polls, campaigns, support tickets, combat tracking, and interactive tactical maps.

Commands work with `/`, `!`, or no prefix when the bot is installed in the server. No-prefix commands must begin with an exact command name and stay on one line.

## 1. Character Management
| Command | Description |
|---------|-------------|
| Paste a Google Sheet link or attach a sheet file | Automatically import, activate, bind, and register the character for Game Master Mode. No command is required. |
| `/importsheet <url>` | Optional manual import from Google Sheets. You can also attach a `.csv`, `.txt`, or `.json` file. |
| `/importjson <url>` | Import from raw JSON (characterswithoutnumber.app). You can also attach a `.json` file. |
| `/update` | Sync your active character with its stored source URL |
| `/link <url>` | Connect a character to a persistent sheet URL for syncing |
| `/threshold_wizard` | Interactive character creation |
| `/language [EN|FR|ES|DE|PT|SV]` | Change bot language |
| `/help` | Overview of all commands. Prefix alias: `!help` |
| `/tutorial` or `tutorial` | Learn rolls, sheets, maps, help, and tickets with a short walkthrough. |
| `/setupguide` or `setupguide` | Recommended server permissions, testing, campaign, map, backup, and diagnostic steps. |
| `/accessibility [mode]` or `accessibility [mode]` | Choose standard, simple/screen-reader-friendly, or private response preferences. |
| `/features`, `!features`, or `features` | Show or change your optional bot features. Server managers can also set server defaults. |
| `ignore me` or `features off bot` | Personal full mute: the bot completely ignores your messages and commands. |
| `listen to me`, `features on bot`, or `/features on bot` | Restore bot access after using personal full mute. |
| `features off voice` or `features off sheets` | Disable only no-prefix voice commands or automatic sheet imports while keeping explicit commands available. |
| `/menu`, `menu`, or `open menu` | Open a button-based menu for dice, characters, maps, help, and support. |
| `/ticket details:<problem> command:</sheet>` or `!ticket <problem>` | Open a support ticket. Also works from a personal app install. |
| `/ticket details:<follow-up> ticket_id:<number>` | Add more information to an existing open ticket. |
| `/tickets`, `/ticketview`, `/ticketreply`, `/ticketclose` | Owner tools to review, reply to, close, or reopen tickets. Ticket views include buttons. |
| `/errors` | Owner-only list of recent runtime errors persisted by the bot for later diagnosis. |
| `/sheet` | View active character (Combat view: `/sc`, Full view: `/sf`) |
| `/switchchar` | `!switchchar` <name> Swap between your imported characters. |
| `/portrait` | `!portrait` [url] Set an image for any of your characters. Attach a file OR paste a URL. Shows as a thumbnail on `/sheet`! |
| `/bind` | `/unbind` 🎭 Associate a character with the current channel. The bot will remember which hero you are playing in each game! |
| `/awardxp` | `!awardxp` <amount> Add XP to active character |
| `/swn` / `/wwn` / `/cwn` | Generate a Level 1 character |
| `/swnhelp` / `/wwnhelp` / `/cwnhelp`| Shorthand quick guides (Stars/Worlds/Cities) |
| `/starthere <system>`| Full quick start guide (SWN/WWN/CWN) |

## 2. Combat & Dice
| Command | Description |
|---------|-------------|
| `/roll <expression>` | Complex rolls: `1d20+1d4+5`, `4d6kh3`, `2d6-1d4`. Use `3x` for multiples! Use commas for mixed rolls (e.g., `!roll ⚔️ 1d20+5, 💥 1d8+2`) |
| `/roll 7x d20` or `!roll d20 7 times` | Roll repeated iterations and show each result vertically in order. |
| `/roll <expression> target N` | Add a target number and the bot reports success/failure. High is default: `!roll d20 target 13`. Use low targets with `!roll d20 target low 13` or `!roll d20 target 13 low`. |
| `/multiroll <num> <exp>` or `!rr <num> <exp>` | Roll the same expression multiple times. Example: `!rr 7 1d20`. |
| `/gmroll <exp>` | Hidden roll (private/ephemeral, use `!gmroll` for prefix) |
| `/attack [weapon]` | Roll attack using sheet modifiers |
| `/skill [name]` | Roll an exact skill from the active sheet (e.g., `!skill notice`). The bot never guesses missing skills or modifiers. |
| `find map forest` or `/maplibrary forest` | Post a visible map directly in Discord. Uses built-in maps, a verified 300+ map library, then test-server-only openly licensed search with creator and license credit. |
| `/initiative` | Roll initiative |
| `/3d6kh` / `/4d6kh` | Specialized rolls (Keep High) |

## 2a. Voice Access & User Install
When the bot is installed in a server, any registered command can be sent without `/` or `!`, such as `roll one d6`, `sheet`, or `help`. The command must start with its exact name or alias and stay on one line.

| Command | Description |
|---------|-------------|
| `/voice <phrase>` | Dictate natural commands through your personal install, such as `roll one d6`, `roll d20 seven times`, `oracle`, `weather`, or `plot`. |
| `/voicehelp` | Show the easiest commands to say with voice tools. |
| `/up` | Show recent messages above this point so you do not need to scroll. |
| `/down` | Show the latest messages in this channel. |
| `/catchup <count>` | Show the last 1-20 readable messages in a compact list. |
| `/roll` and `/multiroll` | Best dice commands when the app is installed for you but not installed on the server. |
| `!commands` | Require the bot to be installed on the server; Discord does not send normal messages to user-installed apps. |

## 3. GM Tracker & Tactical Map
| Command | Description |
|---------|-------------|
| `game master mode` | Start a conversational setup in regular chat. Players only need to import their sheets in the server; no campaign join is required. Enemy HP and AC use a private button. Say `skip` at any question. |
| `/gmmode` | Open the fully hidden one-form setup. Public tracker lists, turn notices, and the web map redact hidden enemy stats. |
| `/tracker add <name> <hp> <ac> [qty]`| Add enemy with Name, HP, AC, and optional Quantity. |
| `/tracker party` | Add all Campaign players to tracker |
| `/tracker map` | Show Tactical Map with interactive movement |
| `/tracker controller` | Launch the in-Discord button-based tactical controller |
| `/importmap <image>` | Upload custom map background |
| `find map forest`, `/maplibrary`, or `!findmap forest` | Post a free downloadable CC0 map from the bot's built-in library. |
| `find portrait operative`, `/portraitlibrary`, or `!findportrait operative` | Post a free downloadable CC0 portrait from the bot's built-in library. |
| `/tracker move <id> <c>` | Move token to coordinates (e.g., `A1`) |
| `/tracker next` | Advance to the next turn |
| `/tracker damage <id> <n>`| Deal damage to a combatant |
| `!botsync` | **IMPORTANT**: Owner command. Use `!botsync guild` (current server) or `!botsync global` if slash commands look wrong. |

## 4. World Building & Factions
| Command | Description |
|---------|-------------|
| `/gen <planet/npc/etc>` | Generate random flavor/stats |
| `/faction create` | Start a new faction |
| `/faction list` | View all global factions |
| `/faction attack` | Perform a faction-level assault |
| `/reaction` | Roll NPC reaction (2d6) |
| `/morale <target>` | Check NPC morale (2d6) |
| `/oracle` | Ask the 2d6 Oracle (Solo/GM) |
| `/plot` | Generate a random plot hook |
| `/loot` | Roll for random flavor loot |

## 5. Party & Campaign
| Command | Description |
|---------|-------------|
| `/campaign start` | Start a new campaign as GM |
| `/campaign join` | Join active campaign as a player |
| `/party info` | View shared party funds and ship status |
| `/party split <amount>` | Calculate even credit distribution |

## 5a. Polls
| Command | Description |
|---------|-------------|
| `/poll question:<text>` | Create a SimplePoll-style Yes/No poll with reactions. |
| `/poll question:<text> answer1:<choice> answer2:<choice>` | Create a multiple-choice reaction poll. Supports up to 10 choices. |
| `!poll "Question?" "Choice A" "Choice B"` | Prefix version using quoted question and choices. Leave choices off for Yes/No. |

## 6. Server Admin (Manage Server required)
| Command | Description |
|---------|-------------|
| `/avatar` | 🖼️ **Change the bot's avatar.** Slash: type `/avatar`, then click the `image` field and upload your file. Prefix: type `!avatar` with an image attached to the same message. PNG/JPG/GIF/WebP, max 8 MB. |
| `/rename <server_id> <name>` | Change the bot's display name for this server. Use `clear` as name to reset. |
| `!botsync guild` | Re-register slash commands for this server (use after updates). |
| `!botsync global` | Sync commands globally (takes up to 1 hour to propagate). |
## 7. Channel Management (Manage Server required)
| Command | Description |
|---------|-------------|
| `/channel role set <role>` | Designate a 'GM' role for the channel. |
| `/channel role info` | View the current channel GM role. |
| `/channel setup <role> <emoji>` | **(Easiest)** Quickly create a join-role message. |
| `!role <emoji> <id> ... [#channel]` | **(Bulk Setup)** Create a single message granting multiple roles to Categories/Channels based on their IDs! Example: `!role 🚀 1111 💰 2222 #welcome` |
| `!rrrole [#channel] @role <emoji>` | Quickly create a simple reaction role message. |
| `/channel reactionrole create` | Create a custom reaction-to-join message. |
| `/channel reactionrole list` | List all active reaction roles in the server. |
| `/channel reactionrole remove <message_id> <emoji>` | Delete a reaction role configuration. |
