# 🎲 Without Number Bot - Command List

All commands work with both `/` (Slash) and `!` (Prefix).

## 1. Character Management
| Command | Description |
|---------|-------------|
| `/importsheet <url>` | Import from Google Sheets (SWN/WWN/CWN). You can also attach a `.csv`, `.txt`, or `.json` file. |
| `/importjson <url>` | Import from raw JSON (characterswithoutnumber.app). You can also attach a `.json` file. |
| `/update` | Sync your active character with its stored source URL |
| `/link <url>` | Connect a character to a persistent sheet URL for syncing |
| `/threshold_wizard` | Interactive character creation |
| `/language [EN|FR|ES|DE|PT|SV]` | Change bot language |
| `/help` | Overview of all commands. Prefix alias: `!help` |
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
| `/roll <expression> target N` | Add a target number and the bot reports success/failure. High is default: `!roll d20 target 13`. Use low targets with `!roll d20 target low 13` or `!roll d20 target 13 low`. |
| `/multiroll <num> <exp>`| Roll same expression multiple times |
| `/gmroll <exp>` | Hidden roll (private/ephemeral, use `!gmroll` for prefix) |
| `/attack [weapon]` | Roll attack using sheet modifiers |
| `/skill [name]` | Roll skill check (e.g., `!skill notice`) |
| `/initiative` | Roll initiative |
| `/3d6kh` / `/4d6kh` | Specialized rolls (Keep High) |

## 3. GM Tracker & Tactical Map
| Command | Description |
|---------|-------------|
| `/tracker add <name> <hp> <ac> [qty]`| Add enemy with Name, HP, AC, and optional Quantity. |
| `/tracker party` | Add all Campaign players to tracker |
| `/tracker map` | Show Tactical Map with interactive movement |
| `/tracker controller` | Launch the in-Discord button-based tactical controller |
| `/importmap <image>` | Upload custom map background |
| `/tracker move <id> <c>` | Move token to coordinates (e.g., `A1`) |
| `/tracker next` | Advance to the next turn |
| `/tracker damage <id> <n>`| Deal damage to a combatant |
| `!sync` | **IMPORTANT**: Use `!sync` (current server) or `!sync global` if commands look wrong! |

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

## 6. Server Admin (Manage Server required)
| Command | Description |
|---------|-------------|
| `/avatar` | 🖼️ **Change the bot's avatar.** Slash: type `/avatar`, then click the `image` field and upload your file. Prefix: type `!avatar` with an image attached to the same message. PNG/JPG/GIF/WebP, max 8 MB. |
| `/rename <server_id> <name>` | Change the bot's display name for this server. Use `clear` as name to reset. |
| `!sync guild` | Re-register slash commands for this server (use after updates). |
| `!sync global` | Sync commands globally (takes ~1 hour to propagate). |
## 7. Channel Management (Manage Server required)
| Command | Description |
|---------|-------------|
| `/channel role set <role>` | Designate a 'GM' role for the channel. |
| `/channel role info` | View the current channel GM role. |
| `/channel setup <role> <emoji>` | **(Easiest)** Quickly create a join-role message. |
| `!role <emoji> <id> ... [#channel]` | **(Bulk Setup)** Create a single message granting multiple roles to Categories/Channels based on their IDs! Example: `!role 🚀 1111 💰 2222 #welcome` |
| `!rr [#channel] @role <emoji>` | Quickly create a simple reaction role message. |
| `/channel reactionrole create` | Create a custom reaction-to-join message. |
| `/channel reactionrole list` | List all active reaction roles in the server. |
| `/channel reactionrole remove <message_id> <emoji>` | Delete a reaction role configuration. |
