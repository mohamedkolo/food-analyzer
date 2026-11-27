import sys,itertools; sys.path.insert(0,'/tmp/fa'); import food_data as F
R={}
for r in F.FOODS: R.setdefault(r["n"],r)
def it(n,gr): r=R[n]; return r["cal"]*gr/100.0, r["p"]*gr/100.0
CH="صدر دجاج"; TU="تونة معلبة بالماء"; EW="بياض بيض"
# fixed pieces of the day (as generated, p339 Thu): strawberries 150, salad 150 (green), soup 380, grilled veg 230, almonds 15, kiwi 230
FIX=[it("فراولة",150),it("سلطة خضراء",150),it("شوربة دجاج",380),it("شوربة دجاج",0),it("لوز",15)]
# veg 230 as in generator resolves to 126 kcal, protein from meal_macros total: use 126 kcal, p=2.5*2.3 approx via 'خضار متنوع'
FIX.append(it("خضار متنوع",230))
fc=sum(x[0] for x in FIX); fp=sum(x[1] for x in FIX)
best=[]
for oats in range(30,81,10):
 for rice in range(60,201,20):
  for chk in range(0,251,10):
   for tu in range(0,201,10):
    for ew in range(0,251,10):
     for kiwi in range(0,231,50):
      c=fc+sum(it(n,g)[0] for n,g in (("شوفان خام",oats),("أرز بني مطبوخ",rice),(CH,chk),(TU,tu),(EW,ew),("كيوي",kiwi)))
      p=fp+sum(it(n,g)[1] for n,g in (("شوفان خام",oats),("أرز بني مطبوخ",rice),(CH,chk),(TU,tu),(EW,ew),("كيوي",kiwi)))
      if abs(c-1560)/1560<=0.05:
        best.append((abs(p-162),round(c),round(p),oats,rice,chk,tu,ew,kiwi))
best.sort()
print("n within 5% kcal:",len(best))
print("closest protein:",best[:3])
# subset needing no more than 1 added protein source beyond existing meal (chicken breast only up to 250)
sub=[b for b in best if b[6]==0 and b[7]==0]
print("chicken-only best:",sub[:1])
sub=[b for b in best if b[5]<=250 and b[6]<=100 and b[7]<=150]
print("moderate (tuna<=100,ew<=150) best:",sub[:1])
co=[b for b in best if b[6]==0 and b[7]==0]
co.sort(key=lambda b:-b[2]); print("chicken-only max protein:",co[:1])
mod=[b for b in best if b[5]<=250 and b[6]<=100 and b[7]<=100]; mod.sort(key=lambda b:abs(b[2]-162)); print("tuna<=100,ew<=100 best:",mod[:1])
