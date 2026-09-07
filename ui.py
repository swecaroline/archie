import discord 
import copy
import math

class CategorySelect(discord.ui.Select):
    def __init__(self, catList, process_categories, multi=False):
        category_max = 1
        if (multi):
            category_max = len(list(copy.deepcopy(catList)))
        super().__init__(
            placeholder="Select an option",
            max_values=category_max,
            min_values=1,
            options=catList,
            id=1
        )
        self.process_categories = process_categories
        self.max_selected = category_max

    async def callback(self, interaction: discord.Interaction):
        await self.process_categories(self.values, interaction)

class CategorySelectView(discord.ui.View):
    PAGE_SIZE = 25
    def __init__(self, *, timeout = 180, multi=False, catList, process_categories, prompt):
        print("Creating view")
        super().__init__(timeout=timeout)
        self.page = 1
        self.option_length = len(catList)
        self.process_categories = process_categories
        self.all_categories = catList
        self.multi = multi
        self.prompt = prompt

        # init with [] for each page
        self.categories_selected = [[] for i in range(math.ceil(self.option_length / self.PAGE_SIZE))]

        # Discord has maximum of 50 categories per server
        # but we are writing this as if there is no limit
        if (self.option_length > self.PAGE_SIZE):
            curr_page = catList[0:self.PAGE_SIZE]
            self.add_pagination_buttons()

            # Only need the submit button if we expect multiple categories to be chosen
            if (multi):
                self.add_submit_button()
            self.add_item(CategorySelect(curr_page, self.process_categories_with_pagination, multi))
        else:
            print("We are here")
            curr_page = catList
            print("2")
            self.add_item(CategorySelect(curr_page, process_categories, multi))
            print("3")

        self.add_no_categories_button()


    def add_pagination_buttons(self):
        can_go_prev = self.page > 1
        can_go_next = self.page < math.ceil(self.option_length / self.PAGE_SIZE)
        if (can_go_prev):
            previous_button = discord.ui.Button(
                label="⬅️ Previous",
                id=3,
            )
            previous_button.callback = self.prev_page
            self.add_item(previous_button)

        if (can_go_next):
            next_button = discord.ui.Button(
                label="➡️ Next",
                id=2,
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    def add_no_categories_button(self):
        no_categories_button = discord.ui.Button(
            label="No category",
            id=4,
            style=discord.ButtonStyle.red
        )
        no_categories_button.callback = self.no_categories
        self.add_item(no_categories_button)

    def add_submit_button(self):
        submit_button = discord.ui.Button(
            label="Submit",
            id=5,
            style=discord.ButtonStyle.green
        )
        submit_button.callback = self.submit_categories
        self.add_item(submit_button)

    async def reset_view(self, interaction):
        self.clear_items()
        start_index = (self.page - 1) * self.PAGE_SIZE
        end_index = self.page * self.PAGE_SIZE
        curr_page = self.all_categories[start_index:end_index]
        self.add_pagination_buttons()
        self.add_no_categories_button()
        if (self.multi):
            self.add_submit_button()
        flat_cats = [f"📁 {item}" for sublist in self.categories_selected for item in sublist]
        prompt = self.prompt
        if (self.multi):
            prompt = f"{self.prompt}\n\n**Currently selected:**\n{"\n".join(flat_cats)}\n"
        self.add_item(CategorySelect(curr_page, self.process_categories_with_pagination, self.multi))
        await interaction.response.edit_message(content=prompt, view=self, delete_after=60)

    async def no_categories(self,interaction: discord.Interaction):
        await self.process_categories([], interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.page += 1
        await self.reset_view(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        self.page -= 1
        await self.reset_view(interaction)

    async def submit_categories(self, interaction: discord.Interaction):
        await self.process_categories([item for sublist in self.categories_selected for item in sublist], interaction)

    async def process_categories_with_pagination(self, values, interaction: discord.Interaction):
        if (self.multi):
            self.categories_selected[self.page - 1] = values
            await self.reset_view(interaction)
        else:
            await self.process_categories(values, interaction)