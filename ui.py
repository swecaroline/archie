import discord 
import copy

class CategorySelect(discord.ui.Select):
    def __init__(self, catList, process_categories, multi=False):
        category_max = 1
        if (multi):
            category_max = len(list(copy.deepcopy(catList)))
            print("CATEGORY MAX" + str(category_max))
        super().__init__(placeholder="Select an option",max_values=category_max,min_values=1,options=catList)
        self.process_categories = process_categories
        self.max_selected = category_max

    async def callback(self, interaction: discord.Interaction):
        await self.process_categories(self.values, interaction)

class CategorySelectView(discord.ui.View):
    def __init__(self, *, timeout = 180, multi=False, catList, process_categories):
        super().__init__(timeout=timeout)
        self.add_item(CategorySelect(catList, process_categories, multi))
