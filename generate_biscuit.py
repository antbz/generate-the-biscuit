import json
import random
import math
import itertools

def normalise_recipe(recipe):
  norm_recipe = {"name": recipe["name"]}
  unique_ingredients = {}
  for i in recipe['ingredients']:
    if i['name'] in unique_ingredients.keys():
      unique_ingredients[i['name']]['amount'] += i['amount']
    else:
      unique_ingredients[i['name']] = i.copy()
  norm_recipe['ingredients'] = list(unique_ingredients.values())

  sum_amounts = sum([i['amount'] for i in recipe['ingredients']])
  scale = 800 / sum_amounts
  for i in norm_recipe['ingredients']:
    i['amount'] = max(1, math.ceil(i['amount'] * scale))
  return norm_recipe

kb = open("knowledgebase.json", "r")
data = json.load(kb)
recipes = [normalise_recipe(recipe) for recipe in data["recipes"]]
ingredients = data["ingredients"]
amount_rules = data["rules"]["amounts"]
special_case_rules = data["rules"]["special cases"]
vegan_alternatives = data["rules"]["vegan alternatives"]


def calculate_proportions(ing_list):
  proportions = {}
  diversity = {}

  for ingredient in ing_list:
    if ingredient["role"] not in proportions:
      proportions[ingredient["role"]] = ingredient["amount"]
      diversity[ingredient["role"]] = 1
    else:
      proportions[ingredient["role"]] += ingredient["amount"]
      diversity[ingredient["role"]] += 1

  base_amount = 0
  for role in ['fat', 'dry', 'liquid', 'sweetener']:
    if role in proportions:
      base_amount += proportions[role]

  additional_amount = 0
  for role in ['add-in', 'topping', 'spice']:
    if role in proportions:
      additional_amount += proportions[role]

  return proportions, diversity, base_amount, additional_amount

def evaluate_proportions(ing_list, initial_score):
    proportions, diversity, base_amount, additional_amount = calculate_proportions(ing_list)

    score = initial_score
    for role in ['fat', 'dry', 'liquid', 'sweetener']:
        if role in proportions:
            if proportions[role]/base_amount > 0.1 and proportions[role]/base_amount < 0.4:
                score += 10
            score += diversity[role]

    if 'add-in' in proportions and 'topping' in proportions and 'spice' in proportions:
        score = 0
    else:
        for role in ['add-in', 'topping', 'spice']:
            if role in proportions:
                score += diversity[role]

    if additional_amount/(additional_amount + base_amount) > 0.5:
        score = 0

    return score

def evaluate_novelty(flavor_combinations, ing_list):
    combos = itertools.combinations([i['name'] for i in ing_list], 2)
    score = 0
    max_times = max(flavor_combinations.items(), key=lambda x:x[1])[1]
    for combo in combos:
        if combo in flavor_combinations:
            score += max_times//flavor_combinations[combo]
        else:
            score += max_times//flavor_combinations[(combo[1], combo[0])]
    return score

def get_flavor_combinations(population):
    combinations = {}
    for recipe in population:
        combos = itertools.combinations([i['name'] for i in recipe["ingredients"]], 2)
        for combo in combos:
            if combo not in combinations:
                if (combo[1], combo[0]) not in combinations:
                    combinations[combo] = 1
                else:
                    combinations[(combo[1], combo[0])] += 1
            else:
                combinations[combo] += 1
                
    return combinations

def evaluate_bounds(ing_list, initial_score):
    score = initial_score
    for ingredient in ing_list:
      if ingredient["name"] in special_case_rules:
        bounds = special_case_rules[ingredient["name"]]
        if ingredient["amount"] < bounds["min"] or ingredient["amount"] > bounds["max"]:
          score = 0
        else:
          score += 10
      else:
        bounds = amount_rules[ingredient["role"]]
        if ingredient['amount'] < bounds["min"] or ingredient['amount'] > bounds["max"]:
          score = 0

    return score

def evaluate_recipes(recipes):
  flavor_combinations = get_flavor_combinations(recipes)
  
  for r in recipes:
    score = evaluate_novelty(flavor_combinations, r["ingredients"])
    score = evaluate_proportions(r["ingredients"], score)
    score = evaluate_bounds(r["ingredients"], score)
  
    r['fitness'] = score

def select_recipe(recipes):
  sum_fitness = sum([recipe['fitness'] for recipe in recipes])
  f = random.randint(0, sum_fitness)
  for i in range(len(recipes)):
    if f < recipes[i]['fitness']:
      return i
    f -= recipes[i]['fitness']
  return -1

def crossover_ingredients(ing1, ing2):
    if len(ing1) == 1:
        p1 = 1
    else:
        p1 = random.randrange(1, len(ing1))
    if len(ing2) == 1:
        p2 = 1
    else:
        p2 = random.randrange(1, len(ing2))
    ing1a = ing1[0:p1]
    ing2b = ing2[p2:-1]
    return ing1a + ing2b

recipe_number = 1

def crossover_recipes(r1, r2):
  global recipe_number

  r = dict()
  r['ingredients'] = []
  for role in ['dry', 'fat', 'sweetener', 'liquid', 'add-in', 'topping', 'spice']:
    ing1 = [ing.copy() for ing in r1['ingredients'] if ing['role'] == role]
    ing2 = [ing.copy() for ing in r2['ingredients'] if ing['role'] == role]
    if len(ing1) > 0 and len(ing2) > 0:
      r['ingredients'].extend(crossover_ingredients(ing1, ing2))
    elif len(ing1) > 0:
      r['ingredients'].extend(ing1)
    elif len(ing2) > 0:
      r['ingredients'].extend(ing2)
  
  r['name'] = "recipe {}".format(recipe_number)
  recipe_number += 1
  
  return r

def get_new_ingredient(role):
    new_ingredient = random.choice(list(ingredients.keys()))
    while role not in ingredients[new_ingredient]['roles']:
      new_ingredient = random.choice(list(ingredients.keys()))
    return {
      "name": new_ingredient,
      "amount": random.randint(amount_rules[role]['min'], amount_rules[role]['max']),
      "unit": ingredients[new_ingredient]["unit"],
      "role": role
    }

def mutate_ingredients(ing, role):
  if len(ing) == 0:
    if role in ['dry', 'fat', 'sweetener', 'liquid']:
      return [get_new_ingredient(role)]
    else:
      m = random.randint(0, 3)
      if m == 0:
        return [get_new_ingredient(role)]
      else:
        return []

  if role in ['topping', 'add-in', 'spice']:
    m = random.randint(0, 1)
    if m == 0:
      return []

  m = random.randint(0, 2)
  # mutate amount
  if m == 0:
    i = random.randint(0, len(ing)-1)
    ing[i]['amount'] = random.randint(
      math.ceil(ing[i]['amount'] * 0.9), 
      math.ceil(ing[i]['amount'] * 1.1))

  # mutate ingredient
  elif m == 1:
    j = random.randint(0, len(ing)-1)
    new_ingredient = random.choice(list(ingredients.keys()))
    while role not in ingredients[new_ingredient]['roles']:
      new_ingredient = random.choice(list(ingredients.keys()))
    ing[j]['name'] = new_ingredient
    ing[j]['unit'] = ingredients[new_ingredient]['unit']

  # add new ingredient
  else:
    ing.append(get_new_ingredient(role))

  return ing

def mutate_recipe(r):
  m = random.randint(0, 5)
  if m == 0:
    new_ingredients = []
    for i in r['ingredients']:
      if ingredients[i['name']]['vegan']:
        new_ingredients.append(i.copy())
      else:
        new_name = random.choice(vegan_alternatives[i['role']])
        new_ingredients.append({
          "name": new_name,
          "amount": i['amount'],
          "unit": ingredients[new_name]["unit"],
          "role": i['role']
        })
    r['ingredients'] = new_ingredients
  else:
    new_ingredients = {role: [] for role in ['dry', 'spice', 'sweetener', 'fat', 'liquid', 'add-in', 'topping']}

    for ingredient in r['ingredients']:
      new_ingredients[ingredient['role']].append(ingredient.copy())
      
    r['ingredients'] = []
    for role, ing in new_ingredients.items():
      r['ingredients'].extend(mutate_ingredients(ing, role))
      
  return r

def generate_recipes(size, population):
  R = []
  while len(R) < size:
    r1 = population[select_recipe(population)]
    r2 = population[select_recipe(population)]
    r = crossover_recipes(r1, r2)
    r = mutate_recipe(r)
    r = normalise_recipe(r)
    R.append(r)
  evaluate_recipes(R)
  return R

def select_population(P, R):
  pop_size = len(P)
  top_x = math.ceil(pop_size/5)

  P.extend(R)
  P = sorted(P, reverse = True, key = lambda r: r['fitness'])

  newP = P[:top_x]
  P = P[top_x:]
  for i in range(pop_size - top_x):
    newP.append(P.pop(select_recipe(P)))
  
  return newP

def create_population():
  population = random.choices(recipes, k=20)

  evaluate_recipes(population)
  population = sorted(population, reverse = True, key = lambda r: r['fitness'])

  max_fitnesses = []
  min_fitnesses = []
  avg_fitnesses = []
  for i in range(1000):
    R = generate_recipes(20, population)
    population = select_population(population, R)
    max_fitnesses.append(population[0]['fitness'])
    min_fitnesses.append(population[-1]['fitness'])
    avg_fitnesses.append(sum([r['fitness'] for r in population]) / len(population))
  
  return population

def format_ingredient_list(ingredients):
  if len(ingredients) == 1:
    return ingredients[0]['name']
    
  return ", ".join([i['name'] for i in ingredients[:-1]]) + " and " + ingredients[-1]['name']

def generate_steps(recipe):
    dry = []
    fat = []
    sweetener = []
    liquid = []
    add_in = []
    topping = []

    for i in recipe['ingredients']:
        if i['role'] == 'dry' or i['role'] == 'spice':
            dry.append(i)
        elif i['role'] == 'fat':
            fat.append(i)
        elif i['role'] == 'sweetener':
            sweetener.append(i)
        elif i['role'] == 'liquid':
            liquid.append(i)
        elif i['role'] == 'add-in':
            add_in.append(i)
        elif i['role'] == 'topping':
            topping.append(i)

    steps = ["Preheat oven to 180C"]

    if len(dry) > 0:
        steps.append(f"In a bowl, whisk {format_ingredient_list(dry)} until combined.")

    if len(sweetener) > 0:
        if len(fat) > 0:
            if len(dry) > 0:
                steps.append(f"In a separate bowl, beat {format_ingredient_list(sweetener)} with the {format_ingredient_list(fat)} until light and fluffy.")
            else:
                steps.append(f"In a bowl, beat {format_ingredient_list(sweetener)} with the {format_ingredient_list(fat)} until light and fluffy.")
        else:
            if len(dry) > 0:
                steps.append(f"Add {format_ingredient_list(sweetener)} to the bowl and whisk.")
            else:
                steps.append(f"In a bowl, whisk {format_ingredient_list(sweetener)} until combined.")
    else:
        if len(fat) > 0:
            if len(dry) > 0:
                steps.append(f"In a separate bowl, beat the {format_ingredient_list(fat)} until light and fluffy.")
            else:
                steps.append(f"In a bowl, beat the {format_ingredient_list(fat)} until light and fluffy.")
    
    if len(liquid) > 0:
        steps.append(f"Add {format_ingredient_list(liquid)} to the mixture and beat on high speed until combined.")

    if len(fat) > 0 and (len(sweetener) > 0 or len(dry) > 0):
        steps.append(f"Slowly incorporate the dry mixture into the wet mixture and beat until combined.")
    
    if len(add_in) > 0:
        steps.append(f"Mix in {format_ingredient_list(add_in)}")

    steps.extend([
        "Cover dough and chill in the fridge for 1 hour.",
        "Form desired amount of balls of dough and place on a baking tray lined with parchment paper.",
        "Bake for 10-15 minutes or until golden brown.",
        f"Remove from oven and let cool for 5 minutes before transferring to a wire rack to cool completely."])
    
    if len(topping) > 0:
        steps.append(f"Decorate with {format_ingredient_list(topping)}.")
    
    return steps

def generate_ingredient_list(recipe):
    ingredients = {role: [] for role in ['dry', 'spice', 'sweetener', 'fat', 'liquid', 'add-in', 'topping']}

    for i in recipe['ingredients']:
        if i['name'] == 'eggs':
            amount = i['amount']/50
            if math.ceil(amount) == 1:
                ingredients[i['role']].append("1 egg")
            else:
                ingredients[i['role']].append(f"{math.ceil(amount)} eggs")
        elif i['name'] == 'egg yolk':
            amount = i['amount']/20
            if math.ceil(amount) == 1:
                ingredients[i['role']].append("1 egg yolk")
            else:
                ingredients[i['role']].append(f"{math.ceil(amount)} egg yolks")
        else:
            if i['unit'] == 'units':
                ingredients[i['role']].append(f"{i['amount']} {i['name']}")
            else:
                ingredients[i['role']].append(f"{i['amount']} {i['unit']} {i['name']}")

    ing_list = []
    for role in ingredients:
        ing_list.extend(ingredients[role])
    return ing_list

def generate_name(recipe):
    categories = {cat:[] for cat in ['add-in', 'topping', 'spice', 'base']}
    isVegan = True
    for ing in recipe["ingredients"]:
        if ing["role"] == "spice":
            categories["spice"] += [(ing["name"], ing["amount"])]
        elif ing["role"] == "add-in":
            categories["add-in"] += [(ing["name"], ing["amount"])]
        elif ing["role"] == "topping":
            categories["topping"] += [(ing["name"], ing["amount"])]
        elif ing["role"] == "dry" and ing["name"] not in ['flour', 'baking soda', 'baking powder', 'salt']:
            categories["base"] += [(ing["name"], ing["amount"])]
        
        if ingredients[ing["name"]]['vegan'] == False:
            isVegan = False

    name = "vegan " if isVegan else ""

    if len(categories["spice"]) == 1:
        name += categories["spice"][0][0] + " "
    elif len(categories["spice"]) > 1:
        sorted_spices = sorted(categories["spice"], reverse=True, key=lambda x:x[1])
        name += sorted_spices[0][0] + " and " + sorted_spices[1][0] + " "

    if len(categories["add-in"]) == 1:
        name += categories["add-in"][0][0] + " "
    elif len(categories["add-in"]) > 1:
        sorted_add_ins = sorted(categories["add-in"], reverse=True, key=lambda x:x[1])
        name += sorted_add_ins[0][0] + " and " + sorted_add_ins[1][0] + " "
    
    if len(categories["base"]) == 1:
        name += categories["base"][0][0] + " "
    elif len(categories["base"]) > 1:
        sorted_bases = sorted(categories["base"], reverse=True, key=lambda x:x[1])
        name += sorted_bases[0][0] + " and " + sorted_bases[1][0] + " "
    
    name += "cookies"

    if len(categories["topping"]) == 1:
        name += " with " + categories["topping"][0][0] + " "
    elif len(categories["topping"]) > 1:
        sorted_toppings = sorted(categories["topping"], reverse=True, key=lambda x:x[1])
        name += " with " + sorted_toppings[0][0] + " and " + sorted_toppings[1][0] + " "
    
    return name

def generate_the_biscuits():
  population = create_population()
  random.shuffle(population)
  output = []
  for recipe in population:
      title = generate_name(recipe)
      recipe_json = {
          "title": title,
          "ingredients": generate_ingredient_list(recipe),
          "steps": generate_steps(recipe)
      }
      output.append(recipe_json)
  return output
