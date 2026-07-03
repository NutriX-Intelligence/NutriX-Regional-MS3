"""
Append Recipe Intelligence Engine JavaScript to index.html
"""
import re

with open('app/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the console.log line near the end
pos = content.rfind("console.log('NutriX AI Diet Planner loaded. Ready!')")
if pos < 0:
    print("Could not find insertion point")
    exit(1)

# Find end of that line
line_end = content.find('\n', pos)
line_end = content.find('\n', line_end + 1)  # second newline after the line

js_code = """
        // ==========================
        // Recipe Intelligence Engine
        // ==========================
        async function findRecipes() {
            const container = document.getElementById('intelResults');
            const errDiv = document.getElementById('intelError');
            const loading = document.getElementById('intelLoading');
            const countSpan = document.getElementById('intelCount');
            const ingredientsStr = document.getElementById('intelIngredients').value.trim();
            if (!ingredientsStr) { errDiv.innerText = 'Please enter at least one ingredient.'; errDiv.style.display = 'block'; return; }
            errDiv.style.display = 'none';
            const ingredients = ingredientsStr.split(',').map(s => s.trim()).filter(s => s);
            if (ingredients.length === 0) { errDiv.innerText = 'Please enter at least one valid ingredient.'; errDiv.style.display = 'block'; return; }
            const payload = {
                ingredients: ingredients,
                goal: document.getElementById('intelGoal').value || null,
                diet_type: document.getElementById('intelDiet').value || null,
                cuisine: document.getElementById('intelCuisine').value || null,
                exclude_ingredients: (document.getElementById('intelExclude').value.trim() || null) ? document.getElementById('intelExclude').value.trim().split(',').map(s => s.trim()).filter(s => s) : null,
                max_cooking_time: document.getElementById('intelMaxTime').value ? parseInt(document.getElementById('intelMaxTime').value) : null,
                top_n: parseInt(document.getElementById('intelTopN').value)
            };
            loading.style.display = 'block';
            container.innerHTML = '';
            countSpan.style.display = 'none';
            try {
                const res = await fetch('/recipes/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!res.ok) { const errData = await res.json(); throw new Error(errData.detail || 'Could not find matching recipes.'); }
                const data = await res.json();
                const recipes = data.top_recipes;
                const total = data.total_results;
                loading.style.display = 'none';
                if (recipes.length === 0) { container.innerHTML = '<div class=\"placeholder-text\">No recipes found matching your ingredients. Try different or fewer ingredients.</div>'; return; }
                countSpan.textContent = 'Showing ' + recipes.length + ' of ' + total + ' matches';
                countSpan.style.display = 'inline-block';
                container.innerHTML = '<div class=\"recipe-list\"></div>';
                const list = container.querySelector('.recipe-list');
                recipes.forEach((r, idx) => {
                    const el = document.createElement('div');
                    el.className = 'recipe-item';
                    el.style.cursor = 'pointer';
                    el.onclick = function() { showRecipeDetail(r.recipe_code); };
                    const matchPct = Math.round(r.match_score * 100);
                    let healthClass = r.health_category === 'Healthy' ? 'badge-score' : r.health_category === 'Unhealthy' ? 'badge-orange' : 'badge-purple';
                    const missing = (r.ingredient_match && r.ingredient_match.missing) || [];
                    const extra = missing.length > 0 ? 'Additional: ' + missing.slice(0, 3).join(', ') + (missing.length > 3 ? '...' : '') : 'All ingredients covered';
                    const bullets = r.reason ? r.reason.split(';').filter(Boolean).map(function(b) { return b.trim(); }).slice(0, 2).join(' | ') : '';
                    let catBadge = 'badge';
                    if (r.category === 'Breakfast') catBadge += ' badge-orange';
                    else if (r.category === 'Snack') catBadge += ' badge-score';
                    else catBadge += ' badge-purple';
                    el.innerHTML = '<div class=\"recipe-info\"><h4 style=\"display:flex;align-items:center;gap:8px;\">' + (idx + 1) + '. ' + r.recipe_name + (r.cuisine ? '<span class=\"badge\">' + r.cuisine + '</span>' : '') + '</h4><div class=\"recipe-meta\"><span class=\"' + catBadge + '\">' + r.category + '</span><span>' + Math.round(r.calories) + ' cal</span><span>' + Math.round(r.protein_g) + 'g P</span><span>' + Math.round(r.carbs_g) + 'g C</span><span>' + Math.round(r.fat_g) + 'g F</span><span>Score: ' + Math.round(r.health_score) + '</span></div><div style=\"font-size:12px;color:var(--text-dim);margin-top:4px;\">' + extra + (bullets ? ' | ' + bullets : '') + '</div></div><div style=\"text-align:right;\"><div class=\"badge score-pill\" style=\"background:rgba(139,92,246,0.12);color:var(--purple);border-color:rgba(139,92,246,0.15);\">Score: ' + r.final_score + '</div><div style=\"margin-top:4px;\"><span class=\"badge ' + healthClass + '\">' + r.health_category + '</span><span class=\"badge\" style=\"background:rgba(59,130,246,0.12);\">' + matchPct + '% match</span></div></div>';
                    list.appendChild(el);
                });
                showNotification('Found ' + total + ' matching recipes!', 'success');
            } catch (err) {
                loading.style.display = 'none';
                errDiv.innerText = err.message;
                errDiv.style.display = 'block';
            }
        }
        async function showRecipeDetail(code) {
            try {
                const res = await fetch('/recipes/' + encodeURIComponent(code));
                if (!res.ok) throw new Error('Could not load recipe details.');
                const data = await res.json();
                const c = document.getElementById('intelResults');
                var ingsHtml = '';
                var ings = data.ingredients || [];
                for (var i = 0; i < ings.length; i++) {
                    var ing = ings[i];
                    var name = ing.food_name || ing.ingredient_name || '-';
                    var extra = ing.amount ? ' (' + ing.amount + ' ' + (ing.unit || '') + ')' : '';
                    ingsHtml += '<li style=\"padding:4px 0;font-size:13px;border-bottom:1px solid var(--card-border);\">' + name + '<span style=\"color:var(--text-dim);\">' + extra + '</span></li>';
                }
                var nutHtml = '';
                if (data.nutrition) {
                    var n = data.nutrition;
                    nutHtml = '<div class=\"metrics-grid\" style=\"margin:0;\"><div class=\"metric-card\" style=\"padding:10px;\"><div class=\"metric-value value-kcal\" style=\"font-size:18px;\">' + Math.round(n.energy_kcal) + '</div><div class=\"metric-label\">Calories</div></div><div class=\"metric-card\" style=\"padding:10px;\"><div class=\"metric-value value-prot\" style=\"font-size:18px;\">' + Math.round(n.protein_g) + 'g</div><div class=\"metric-label\">Protein</div></div><div class=\"metric-card\" style=\"padding:10px;\"><div class=\"metric-value value-carb\" style=\"font-size:18px;\">' + Math.round(n.carb_g) + 'g</div><div class=\"metric-label\">Carbs</div></div><div class=\"metric-card\" style=\"padding:10px;\"><div class=\"metric-value value-fat\" style=\"font-size:18px;\">' + Math.round(n.fat_g) + 'g</div><div class=\"metric-label\">Fat</div></div></div>';
                } else {
                    nutHtml = '<div class=\"placeholder-text\" style=\"padding:16px;\">No nutrition data</div>';
                }
                var instrHtml = '';
                if (data.instructions) {
                    instrHtml = '<div style=\"margin-top:12px;\"><h3 style=\"font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text-muted);\">Instructions</h3><p style=\"font-size:13px;color:var(--text-muted);line-height:1.7;white-space:pre-wrap;\">' + data.instructions + '</p></div>';
                }
                var cuisineBadge = data.cuisine ? '<span class=\"badge badge-purple\">' + data.cuisine + '</span>' : '';
                var diffBadge = data.difficulty ? '<span class=\"badge badge-orange\">' + data.difficulty + '</span>' : '';
                var timeBadge = data.cooking_time_minutes ? '<span class=\"badge badge-score\">' + data.cooking_time_minutes + ' min</span>' : '';
                c.innerHTML = '<div class=\"card\" style=\"padding:20px;margin-bottom:16px;\"><div style=\"display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;\"><div><h2 style=\"font-size:20px;font-weight:700;margin-bottom:4px;\">' + data.recipe_name + '</h2><div style=\"display:flex;gap:8px;font-size:13px;color:var(--text-muted);flex-wrap:wrap;\"><span class=\"badge\">' + data.category + '</span>' + cuisineBadge + diffBadge + timeBadge + '</div></div><div style=\"text-align:right;\"><div style=\"font-size:28px;font-weight:800;color:var(--purple);\">' + (data.health_score ? Math.round(data.health_score) : '-') + '</div><div style=\"font-size:12px;color:var(--text-muted);\">Health Score ' + (data.health_category || '') + '</div></div></div><div style=\"margin:16px 0;display:flex;gap:24px;flex-wrap:wrap;\"><div style=\"flex:2;min-width:200px;\"><h3 style=\"font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text-muted);\">Ingredients</h3><ul style=\"list-style:none;padding:0;\">' + ingsHtml + '</ul></div><div style=\"flex:1;min-width:150px;\"><h3 style=\"font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text-muted);\">Nutrition (per 100g)</h3>' + nutHtml + '</div></div>' + instrHtml + '<button class=\"btn btn-sm btn-outline\" onclick=\"findRecipes()\" style=\"width:auto;margin-top:16px;\">Back to Results</button></div>';
                c.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } catch (err) { showNotification('Error: ' + err.message, 'error'); }
        }
"""

# Insert after the line with the second newline
before = content[:line_end]
after = content[line_end:]
new_content = before + js_code + after

with open('app/templates/index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully appended Recipe Intelligence JavaScript!")
