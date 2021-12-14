import uuid

import utils
from utils.context import Context
from utils.views import confirm


class Country(utils.discord.ui.Select):
    def __init__(self, embed):
        countries = {
            "Venezuela", 
            "Colombia", 
            "Ecuador", 
            "Argentina", 
            "EE.UU", 
            "México", 
            "Chile", 
            "Trinidad y Tobago", 
            "Puerto Rico", 
            "Brasil", 
            "El Salvador", 
            "Paraguay", 
            "Uruguay", 
            "Nicaragua", 
            "Japon", 
            "España", 
            "República Domina", 
            "Guatemala", 
            "Peru", 
            "Bolivia", 
            "Panamá" 
        }
                
        options = []
        for country in countries:
            options.append(utils.discord.SelectOption(label=country, description=f"Actualmente resides en {country}"))

        super().__init__(placeholder='Elije tu País de residencia ...', min_values=1, max_values=1, options=options)
        self.embed: utils.discord.Embed = embed

    async def callback(self, interaction: utils.discord.Interaction):
        try: 
            self.embed.set_field_at(0, name="País de residencia:", value=f"```{self.values[0]}```", inline=True)
        except:
            self.embed.insert_field_at(0, name="País de residencia:", value=f"```{self.values[0]}```", inline=True)
        await interaction.response.edit_message(embed=self.embed)


class Question(utils.discord.ui.Select):
    def __init__(self, embed):
        options = [
            utils.discord.SelectOption(label="Diversion", emoji="🥳"),
            utils.discord.SelectOption(label="Por el nitro", emoji="🤑"),
            utils.discord.SelectOption(label="Ambas", emoji="👍")
        ]
        
        super().__init__(placeholder='¿Por que participas?', min_values=1, max_values=1, options=options)
        self.embed: utils.discord.Embed = embed
        
    async def callback(self, interaction: utils.discord.Interaction):
        try:
            self.embed.set_field_at(1, name="¿Por que participas?:", value=f"```{self.values[0]}```", inline=True)
        except:
            self.embed.insert_field_at(1, name="¿Por que participas?:", value=f"```{self.values[0]}```", inline=True)
        await interaction.response.edit_message(embed=self.embed)
        

class Form(utils.discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx: Context = ctx
        self.embed: utils.discord.Embed = utils.discord.Embed(title='Formulario', colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
        
        self.country = Country(self.embed)
        self.add_item(self.country)
        
        self.question = Question(self.embed)
        self.add_item(self.question)
        
    @utils.discord.ui.button(label='Enviar', style=utils.discord.ButtonStyle.red)
    async def send(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        document = utils.db.Document(collection="tournamentc", document="participants")

        if len(document.content) >= 32:
            await interaction.response.send_message("Ups!, ya se lleno el limite de inscripciones :(\nSe mas rapido la proxima vez!")
            return await self.ctx.message.add_reaction('❌')

        if utils.is_empty(self.country.values) or utils.is_empty(self.question.values):
            return await interaction.response.send_message('Creo que te falta contestar el formulario <:awita:852216204512329759>', ephemeral=True)

        document.update(str(self.ctx.author.id), {"name": f"{self.ctx.author.name}#{self.ctx.author.discriminator}", 
                                                  "pfp": self.ctx.author.avatar.url,
                                                  "country": self.country.values[0],
                                                  "question": self.question.values[0]})

        for role in self.ctx.guild.roles:
            if role.id == 912816678818172968:
                await self.ctx.author.add_roles(role)
        
        await interaction.response.send_message("Listo! , se envio tu inscripción correctamente :D\nAhora toca esperar las indicaciones de los admins :)", ephemeral=True)
        await self.ctx.message.add_reaction('✔')

        avatar = self.ctx.author.guild_avatar.url if self.ctx.author.guild_avatar is not None else self.ctx.author.avatar.url
        channel = self.ctx.bot.get_channel(911764720481107989)

        embed = utils.discord.Embed(title = "Nuevo Jugador Inscrito", description = f"{self.ctx.author.mention} ahora es un rival más", color = utils.discord.Colour.blue())
        embed.set_thumbnail(url=avatar)
        embed.set_image(url="https://cdn.discordapp.com/attachments/850419367573061653/913920854709129326/unknown.png")
        embed.set_author(name = f"{self.ctx.author.name}#{self.ctx.author.discriminator}", icon_url = self.ctx.author.avatar.url)
        await channel.send(embed = embed)

        self.stop()

    async def on_timeout(self):
        await self.ctx.author.send("Se te acabó el tiempo, intenta pensarlo antes de navidad 🙄")


class Player:
    def __init__(self, user_id):
        self._document = utils.db.Document(collection="tournamentcx", document="participants")
        self.id = str(user_id)
    
    @property
    def data(self) -> dict:
        return self._document.content.get(self.id)
    
    @property
    def name(self) -> str:
        return self.data.get('name')
    
    def delete(self):
        self._document.delete(self.id)

class Game:
    def __init__(self, ctx: Context, game_id):
        self.ctx = ctx
        self.id = str(game_id)
        self._document = utils.db.Document(collection="tournamentcx", document="games")
        self._waiting = utils.db.Document(collection="tournamentcx", document="games", subcollection="waiting", subdocument=self.id)
        self._finished = utils.db.Document(collection="tournamentcx", document="games", subcollection="finished", subdocument=self.id)
    
    @property
    def waiting(self):
        return self._waiting.exists
    
    @property
    def playing(self):
        if utils.is_empty(self._document.content.get("playing")):
            return None
        
        return self._document.content.get("playing").get("game_id") == self.id
    
    @property
    def finished(self):
        return self._finished.exists
    
    @property
    def opponents(self) -> dict[Player] or None:
        if self.waiting:
            return {player_id: Player(player_id) for player_id in self._waiting.content.get("opponents")}
        elif self.finished:
            return {player_id: Player(player_id) for player_id in self._finished.content.get("opponents")}
        elif self.playing: 
            return {player_id: Player(player_id) for player_id in self._document.content.get("playing").get("opponents")}
        else: return None
        
    async def start(self):
        if self.waiting == False:
            return await self.ctx.send("Nop, nada que ver por aqui, la partida no existe o ya fue terminada <:awita:852216204512329759>")
        
        data = self._waiting.content
        data["game_id"] = self.id
        data["game_link"] = None
        
        if self.playing is None:
            self._waiting.delete()
            self._document.update("playing", data)

            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    await self.ctx.author.add_roles(role)
                    
            await self.ctx.send("Partida iniciada!")
        else:
            await self.ctx.send("Lo siento, ya hay una partida en curso 🙄")
    
    async def winner(self, user_id):
        if self.playing:
            opponents = self.opponents
            data = self._document.content.get("playing")
            data.pop("game_id")
            for player_id, player_object in opponents.items():
                if player_id == str(user_id):
                    data["winner"] = player_object.id
                else:
                    player_object.delete()

            self._document.delete("playing")
            self._finished.set(content=data)
            
            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    await self.ctx.author.remove_roles(role)
            
            await self.ctx.send("Partida finalizada y ganador establecido")
        else: 
            await self.ctx.send("No se puede definir a un ganador porque este juego no se a iniciado 🙄")
        
    def delete(self):
        self._waiting.delete()


class Tournament_Chess(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @utils.commands.command(hidden=True)
    async def inscription(self, ctx: Context):
        return await ctx.send("Ups!, Lamentablemente ya se cerraron las inscripciones :(")
        
        if ctx.guild is None:
            return

        form = Form(ctx)
        await ctx.author.send("Pronto estará lista tu inscripción al torneo!, solo necesitamos que llenes este pequeño formulario:", embed=form.embed, view = form)

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def players(self, ctx: Context, member: utils.discord.Member=None):
        if member is not None:
            player = Player(member.id)
            
            embed: utils.discord.Embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name=player.name, icon_url=player.data.get('pfp'))
            embed.add_field(name="ID:", value=f"`{player.id}`")
            embed.add_field(name="Country:", value=f"`{player.data.get('country')}`")
            embed.add_field(name="Question:", value=f"`{player.data.get('question')}`")
            
            await ctx.send(embed=embed)
        else:    
            num = 1
            players = utils.db.Document(collection="tournamentcx", document="participants")
            for user_id, data in players.content.items():
                embed: utils.discord.Embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
                embed.set_author(name=data.get('name'), icon_url=data.get('pfp'))
                embed.add_field(name="ID:", value=f"`{user_id}`")
                embed.add_field(name="Country:", value=f"`{data.get('country')}`")
                embed.add_field(name="Question:", value=f"`{data.get('question')}`")
                
                await ctx.send(f"#{num}", embed=embed)
                num += 1

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def remove_player(self, ctx: Context, member: utils.discord.Member):
        player = Player(member.id)

        view = confirm.Confirm()
        await ctx.send(f"Seguro que quieres descalificar a {member.name}#{member.discriminator}?", view=view)

        await view.wait()
        if view.value is None:
            await ctx.send("Se te acabó el tiempo, intenta pensarlo antes de navidad 🙄")
        elif view.value:
            player.delete()
            await ctx.send(f"{member.name}#{member.discriminator} fue descalificado :(")

        
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def generate_games(self, ctx: Context):
        collection = utils.db.Collection(collection="tournamentcx", document="games", subcollection="waiting")
        collection.delete()
        
        players = list(utils.db.Document(collection="tournamentcx", document="participants").content.keys())
        while utils.is_empty(players) == False:
            if len(players) == 1:
                break

            player1 = Player(utils.random.choice(players))
            players.pop(players.index(player1.id))
            
            player2 = Player(utils.random.choice(players))
            players.pop(players.index(player2.id))
            
            id = str(uuid.uuid1().int)
            collection.set(id, opponents=[player1.id, player2.id])
            
            await ctx.send("Partidas generadas exitosamente!")
            
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def games(self, ctx: Context, game_id=None):
        if game_id is not None:
            game = Game(ctx, game_id)
            embed = utils.discord.Embed(title="Game", colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.add_field(name="ID:", value=f"```{game.id}```", inline=False)
            
            num = 1
            for player in game.opponents.values():
                embed.add_field(name=f"Player {num}:", value=f"```{player.name}/{player.id}```")
                num += 1
                
            await ctx.send(embed=embed)
        else: 
            num = 1
            waiting = utils.db.Collection(collection="tournamentcx", document="games", subcollection="waiting")
            for game_document in waiting.documents():
                game = Game(ctx, game_document.id)
                embed = utils.discord.Embed(title=f"Game #{num}", colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
                embed.add_field(name="ID:", value=f"```{game.id}```", inline=False)

                _num = 1
                for player in game.opponents.values():
                    embed.add_field(name=f"Player {_num}:", value=f"```{player.name}/{player.id}```")
                    _num += 1
                
                await ctx.send(embed=embed)
                num += 1

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def start_game(self, ctx: Context, game_id):
        game = Game(ctx, game_id)
        await game.start()
        
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def winner(self, ctx: Context, member: utils.discord.Member):
        playing = utils.db.Document(collection="tournamentcx", document="games").content.get("playing", {})
        if utils.is_empty(playing):
            await ctx.send("No se puede definir a un ganador porque no hay ningun juego iniciado 🙄")
        else:
            game = Game(ctx, playing.get("game_id"))
            await game.winner(member.id)
        

def setup(bot):
    bot.add_cog(Tournament_Chess(bot))
