#   ---------------------------------------------------------------------------------
#   SIMPLE DIFFICULTY ANALYSIS SCRIPT
#   The following script takes a CD2 difficulty file and prints a chart with all the enemies it can 
#   find , including those in the vanilla pool by default. Basic usage:
#   Help:
#           python3 diff_analyzer.py -- help 
#
#   Difficulty chart sorted alphabetically by enemy (default):

#           python3 diff_analyzer.py "path_to_difficulty.json"

#   Difficulty chart sorted by some other field:

#           python3 diff_analyzer.py "path_to_difficulty.json" --sort-by "Rarity"

#   Accepted fields for --sort-by: ["Rarity", "SpawnAmountModifier", "Encounters", "ConstantPressure,
#                                   "DifficultyRating", "Pool"]
#   
#   An enemy will be shown in the unknown pool if the diff contains its descriptor 
#   but it's not in any of the pools (could be a mistake, could be an enemy used in a wavespawner,
#   or could be an enemy that is added or removed to the pool by mutation).
#   There is a flag for filtering enemies in the unknown pool: --filter--unknown
#
#   Asterisks (*) in numbers indicate that those are tha vanilla values for an enemy.
#   ---------------------------------------------------------------------------------

import json
import click
from tabulate import tabulate

VANILLA_DESCRIPTORS = 'VanillaEnemyDescriptors.json'
MOD_DESCRIPTORS = 'ModDescriptors.json'
VANILLA_COMMON_POOL = {
        "ED_Spider_Grunt",
        "ED_Spider_Tank",
        "ED_Spider_ShieldTank",
        "ED_Spider_RapidShooter",
        "ED_Spider_Buffer",
        "ED_Spider_ExploderTank",
        "ED_Spider_Stinger",
        "ED_Woodlouse",
        "ED_Grabber",
        "ED_Bomber",
        "ED_Spider_Swarmer",
        "ED_Spider_Exploder",
        "ED_Spider_Spitter",
        "ED_Spider_Shooter",
        "ED_Spider_Lobber",
        "ED_Mactera_Shooter_Normal",
        "ED_Mactera_TripleShooter",
        "ED_Spider_Stalker"
    }

VANILLA_STATIONARY_POOL = {
        "ED_ShootingPlant",
        "ED_CaveLeech",
        "ED_TentaclePlant",
        "ED_BarrageInfector",
        "ED_JellyBreeder",
        "ED_SpiderSpawner"
    }

def remove_multilines(diff):
    s = ""
    multiline = False
    for line in diff.readlines():
        if not multiline:
            if line.strip().startswith("\"Description") and not line.strip().endswith("\","):
                # Multilines detected
                multiline = True
                s += line.strip() + "\","
                continue
            s += line
        else:
            if line.strip().startswith("\"") and line.strip() != "\",":
                multiline = False 
                s += line

    return s

def build_enemy_record(diff_file) -> list:
    with open(VANILLA_DESCRIPTORS, 'r') as f:
        vanilla_record = json.load(f)

    with open(MOD_DESCRIPTORS, 'r') as f:
        mod_record = json.load(f)

    def search_for_control(control: str, default="N/A"):
        if p := diff_file.get("Enemies", {}).get(enemy, {}).get(control):
            if isinstance(p, dict):
                return "Mutated"
            else:
                return p
        elif p := diff_file.get("EnemiesNoSync", {}).get(enemy, {}).get(control):
            if isinstance(p, dict):
                return "Mutated"
            else:
                return p
        elif p := vanilla_record.get(enemy, {}).get(control):
            return f"{p} (*)"
        elif p := mod_record.get(enemy, {}).get(control):
            return f"{p} (*)"
        else:
            return default

    def search_for_origin(enemy):
        if b := diff_file.get("Enemies", {}).get(enemy, {}).get("Base"):
            base = b 
        elif b := diff_file.get("EnemiesNoSync", {}).get(enemy, {}).get("Base"):
            base = b 
        else:
            base = enemy 

        if base in vanilla_record:
            return f"{base} / Vanilla"
        elif base in mod_record:
            if base_origin := mod_record[base].get("EnemyClass", {}).get("AssetPathName"):
                if "Elytras" in base_origin:
                    origin = "EEE"
                elif "Donnie" in base_origin:
                    origin = "DEA"
                elif "yinny" in base_origin:
                    origin = "MEV"
                else:
                    origin = "unknown"
            else:
                origin = "unknown"
            return f"{base} / {origin}"
        else:
            return "unknown"

    record = []
    for pool, enemies in build_enemy_pools(diff_file).items():
        for enemy in enemies:
            record.append({
                "Enemy": enemy,
                "Base/Origin": search_for_origin(enemy),
                "Rarity": search_for_control("Rarity"),
                "DifficultyRating": search_for_control("DifficultyRating"),
                "SpawnAmountModifier": search_for_control("SpawnAmountModifier"),
                "Encounters": search_for_control("CanBeUsedInEncounters", default="False"),
                "ConstantPressure": search_for_control("CanBeUsedForConstantPressure", default="False"),
                "Pool": pool
            })
    return record

def build_enemy_pools(diff: dict) -> dict:

    diff_pools = diff["Pools"]
    if "Enemies" in diff:
        diff_enemies = diff["Enemies"]
    elif "EnemiesNoSync" in diff:
        diff_enemies = diff["EnemiesNoSync"]
    else:
        diff_enemies = {}
    
    def get_enemies_from_pool(pool):
        add, remove = set(), set()
        if pool in diff_pools:
            if "add" in [k.lower() for k in  diff_pools[pool]]:
                for enemy_list in [diff_pools[pool].get(s, {}) for s in ["add", "Add", "ADD"]]:
                    for enemy in enemy_list:
                        if isinstance(enemy, str):
                            add.add(enemy)
            if "remove" in [k.lower() for k in diff_pools[pool]]:
                for enemy_list in [diff_pools[pool].get(s, {}) for s in ["Remove", "REMOVE", "remove"]]:
                    for enemy in enemy_list:
                        if isinstance(enemy, str):
                            remove.add(enemy)
        return add, remove
    
    common_pool = VANILLA_COMMON_POOL
    for pool in ["EnemyPool", "DisruptiveEnemies", "SpecialEnemies", "CommonEnemies"]:
        enemies_to_add, enemies_to_remove = get_enemies_from_pool(pool)
        common_pool = common_pool | enemies_to_add - enemies_to_remove

    stationary_pool = VANILLA_STATIONARY_POOL
    enemies_to_add, enemies_to_remove = get_enemies_from_pool("StationaryPool")
    stationary_pool = stationary_pool | enemies_to_add - enemies_to_remove

    unknown_pool = (diff_enemies.keys() - common_pool) & (diff_enemies.keys() - stationary_pool)
    
    return {"enemy_pool": common_pool, 
            "stationary_pool": stationary_pool,
            "unknown": unknown_pool}

def custom_sorter(s, sort_by):
    
    fields = {
        "Enemy": "str",
        "Rarity": "numeric",
        "Pool": "str",
        "SpawnAmountModifier": "numeric", 
        "DifficultyRating": "numeric",
        "Encounters": "bool",
        "ConstantPressure": "bool"
    }
    
    match fields[sort_by]:
        case "str":
            return s 
        case "bool":
            return str(s)
        case _:
            if isinstance(s, str):
                if s.endswith("(*)"):
                    return float(s.split()[0])
                return -1
            elif isinstance(s, list):
                return s[0]
            else:
                return s

@click.command()
@click.option("--sort-by", default="Enemy", 
              type=click.Choice(["Enemy", "Rarity", "SpawnAmountModifier", "Encounters", "DifficultyRating", "Pool", "ConstantPressure"]),
              help="The chart will be sorted by this column.")
@click.option("--filter-unknown", is_flag=True, default=False, help="If specified, will filter enemies with unknown pool.")
@click.argument('file_path')
def sort_and_plot(file_path: str, sort_by: str, filter_unknown: bool):

    with open(file_path, 'r') as diff:
        diff_file = json.loads(remove_multilines(diff))

    enemy_record = build_enemy_record(diff_file)
    if filter_unknown:
        enemy_record = [rc for rc in enemy_record if rc["Pool"] != "unknown"]
    sorted_record = sorted(enemy_record, 
                           key=lambda r: custom_sorter(r[sort_by], sort_by))
    print(f"\nCHART FOR: {diff_file.get('Name', 'Unknown')}")
    print(tabulate(sorted_record, headers="keys"))

if __name__ == '__main__':
    sort_and_plot()


