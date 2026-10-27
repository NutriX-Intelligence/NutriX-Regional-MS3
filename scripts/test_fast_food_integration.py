import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('=== Test 1: Fast Food Chains Summary ===')
res = client.get('/api/fast-food/chains')
print('Status:', res.status_code)
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
chains = res.json()
print(f'Found {len(chains)} chains:')
for c in chains:
    print(f"  - {c['icon']} {c['brand']}: {c['total_items']} items (Veg: {c['veg_count']}, Non-Veg: {c['non_veg_count']}, Jain: {c['jain_count']}, Vegan: {c['vegan_count']}, Avg: {c['avg_calories']} kcal)")
assert len(chains) == 8, f"Expected 8 chains, got {len(chains)}"

print('\n=== Test 2: Grouped Domino\'s with Veg filter ===')
res = client.get('/api/fast-food/grouped?brand=dominos&diet_filter=Vegetarian')
print('Status:', res.status_code)
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
groups = res.json()
total_items = sum(grp['item_count'] for grp in groups)
print(f"Total Domino's Veg items returned across groups: {total_items}")
for grp in groups:
    print(f"Brand: {grp['brand']} | Items: {grp['item_count']} | Veg: {grp['veg_count']} | Non-Veg: {grp['non_veg_count']}")
    assert grp['non_veg_count'] == 0, "Vegetarian filter should exclude Non-Veg items!"
    for sec in grp['sections']:
        print(f"  Section: {sec['section_name']} ({len(sec['items'])} items)")
        for item in sec['items'][:2]:
            print(f"    * {item['recipe_name']} | {item['energy_kcal']} kcal | P:{item['protein_g']}g C:{item['carb_g']}g F:{item['fat_g']}g | {item['dietary_tag']}")

print('\n=== Test 3: Grouped KFC with Non-Veg filter ===')
res = client.get('/api/fast-food/grouped?brand=kfc&diet_filter=Non-Vegetarian')
assert res.status_code == 200
kfc_groups = res.json()
kfc_total = sum(grp['item_count'] for grp in kfc_groups)
print(f"Total KFC Non-Veg items returned: {kfc_total}")
for grp in kfc_groups:
    print(f"Brand: {grp['brand']} | Items: {grp['item_count']} | Non-Veg: {grp['non_veg_count']} | Veg: {grp['veg_count']}")
    assert grp['veg_count'] == 0, "Non-Vegetarian filter should exclude Veg items!"
    for sec in grp['sections'][:2]:
        print(f"  Section: {sec['section_name']} ({len(sec['items'])} items)")

print('\n=== Test 4: Recommend Foods (Catalog Search) for "dominos" ===')
res = client.post('/recommend-foods', json={'user_id': 1, 'query': 'dominos', 'limit': 10, 'diet_filter': 'Vegetarian'})
print('Status:', res.status_code)
assert res.status_code == 200
rec_items = res.json()
print(f"Found {len(rec_items)} recommendations for 'dominos'. First 3:")
for item in rec_items[:3]:
    print(f"  - {item['recipe_name']} ({item.get('brand')}) | {item['energy_kcal']} kcal | {item.get('dietary_tag')}")

print('\n=== Test 5: Meal Logging a Fast Food Item ===')
# Pick the first Domino's veg item
sample_item = groups[0]['sections'][0]['items'][0]
log_payload = {
    'user_id': 1,
    'food_name': f"{sample_item['brand']} - {sample_item['recipe_name']}",
    'meal_type': 'Lunch',
    'calories': sample_item['energy_kcal'],
    'protein': sample_item['protein_g'],
    'carbs': sample_item['carb_g'],
    'fat': sample_item['fat_g']
}
res_log = client.post('/api/meal-logs', json=log_payload)
print('Log Status:', res_log.status_code)
assert res_log.status_code == 201
log_data = res_log.json()
print(f"Logged meal ID: {log_data['id']}, Food: {log_data['food_name']}, Calories: {log_data['calories']}")

# Check today's meal logs for user 1
res_today = client.get('/api/meal-logs/today/1')
print('Today logs Status:', res_today.status_code)
assert res_today.status_code == 200
today_data = res_today.json()
logged_names = [item['food_name'] for item in today_data.get('logs', [])]
print(f"Today logged items count: {len(logged_names)}")
assert log_data['food_name'] in logged_names, f"Expected {log_data['food_name']} in today's logs!"

print('\n' + '='*50)
print('ALL TESTS PASSED SUCCESSFULLY! Fast food integration is verified.')
print('='*50)
