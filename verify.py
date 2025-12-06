import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, InputText, Modal
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "verify_settings.json"

def load_settings():
    if not os.path.exists(DATA_FILE):
        save_settings({
            "verify_code": None,
            "verify_channel": None,
            "apply_channel": None,
            "log_channel": None,
            "member_role": None,
            "unverified_role: None
        })
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

settings = load_settings()

intents = discord.Intents.dafault()
intents.members = True
bot = commands.Bot(command_prefix="?$", intents=intents)

#認証コード入力モーダル
class CodeInputModal(Modal, title="認証コードの入力"):
    code = InputText(label="認証コードを入力してください")
    
    async def callback(self, interaction: discord.Interaction):
        settings = load_settings()
        verify_code = settings["verify_code"]
        
        member_role_id = settings.get("member_role")
        unverified_role_id = settings.get("unverified_role")
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        
        embed = discord.Embed()
        embed.add_field(name="送信した認証コード", value=self.code.value, inline=False)
        
        if self.code.value != verify_code:
            embed.title = "❌認証コードが違います。"
            embed.color = discord.Color.red()
            
            try:
                await interaction.user.send(embed=embed)
            except:
                pass
            
            return await interaction.response.send_message("❌認証コードが違います", ephemeral=True)
            
        embed.title = "✅認証コードで認証を完了しました。"
        embed.color = discord.Color.green()
        
        try:
            await interaction.user.send(embed=embed)
        except:
            pass
        
        try:
            if unverified_role_id:
                unverified_role = guild.get_role(unverified_role_id)
                if unverified_role in member.roles:
                    await member.remove_roles(unverified_role)
                    
            if member_role_id:
                member_role = guild.get_role(member_role_id)
                if member_role not in member.roles:
                    await member.add_roles(member_role)
        except Exception as e:
            print(f"ロール付与エラー: {e}")
            
        return await interaction.response.send_message("✅認証が完了しました。", ephemeral=True)

#認証申請フォーム
class VerifyApplyModal(Modal, title="認証申請フォーム"):
    name = InputText(label="あなたの名前を入力してください")
    inviter = InputText(label="誰から招待されましたか？")
    message = InputText(label="管理者への一言(任意)", required=False)
    
    async def callback(self, interaction: discord.Interaction):
        settings = load_settings()
        apply_channel_id = settings["apply_channel"]
        
        if not apply_channel_id:
            return await interaction.response.send_message("管理側の認証申請設定が完了していません。サーバー管理者に問い合わせてください。", ephemeral=True)
            
        apply_channel = interaction.guild.get_channel(apply_channel_id)
        
        embed = discord.Embed(
            title="🔐 認証申請",
            description=f"ユーザー: {interaction.user.mention}\nID: `{interaction.user.id}`",
            color=discord.Color.yellow()
        )
        embed.add_field(name="名前", value=self.name.value, inline=False)
        embed.add_field(name="招待者", value=self.inviter.value, inline=False)
        embed.add_field(name="一言", value=self.message.value, inline=False)
        
        await apply_channel.send(
            embed=embed,
            view=VerifyApprovalView(
                interaction.user.id,
                self.name.value,
                self.inviter.value,
                self.message.value or "(なし)"
            )
        )
        
        await interaction.response.send_message("📨 認証申請を送信しました。管理者の承認をお待ち下さい。", ephemeral=True)
        
        try:
            dm_embed = discord.Embed(
                title="📬 認証申請が完了しました",
                description="管理者の承認をお待ち下さい。",
                color=discord.Color.blue()
            )
            dm_embed.add_field(name="申請内容", value=None, inline=False)
            dm_embed.add_field(name="あなたの名前を入力してください", value=name, inline=False)
            dm_embed.add_field(name="誰から招待されましたか？", value=inviter, inline=False)
            dm_embed.add_field(name="管理者への一言(任意)", value=message, inline=False)

            await interaction.user.send(embed=dm_embed)
        except:
            pass

#認証申請承認&拒否ボタン
class VerifyApprovalView(View):
    def __init__(self, user_id, name, inviter, message):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.name = name
        self.inviter = inviter
        self.message = message
                
    @discord.ui.button(label="✅承認", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: Button):
        settings = load_setting()
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        unverified_role = guild.get_role(settings["unverified_role"])
        member_role = guild.get_role(settings["member_role"])
        log_channel = guild.get_channel(settings["log_channel"])
                
        if unverified_role in user.roles:
            await user.remove_roles(unverified_role)
        if member_role:
            await user.add_roles(member_role)
                
        await interaction.response.edit_message(
            content=f"✅ {user.display_name} の認証申請を承認しました。", view=None
        )
        try:
            approve_embed = discord.Embed(
                title="✅ 認証申請が承認されました",
                description="メンバーロールが付与されました。",
                color=discord.Color.green()
            )
            await user.send(embed=approve_embed)
        except:
            pass
        
        if log_channel:
            log_embed = discord.Embed(
                title=f"✅ {user.mention} の認証申請が承認されました",
                description=None,
                color=discord.Color.green()
            )
            log_embed.add_field(name="あなたの名前を入力してください", value=name, inline=False)
            log_embed.add_field(name="誰から招待されましたか？", value=inviter, inline=False)
            log_embed.add_field(name="管理者への一言(任意), value=message, inline=False)
            log_embed.set_footer(text=f"担当者: {interaction.user.mention}")
        
            await log_channel.send(embed=log_embed)
            
    @discord.ui.button(label="❌拒否", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: Button):
        settings = load_settings()
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        log_channel = guild.get_channel(settings["log_channel"])
        
        await interaction.response.edit_message(
            content=f"❌ {user.display_name} の認証申請を拒否しました。", view=None
        )
        
        embed = discord.Embed(
            title="❌ 認証申請が拒否されました",
            description="申請内容を再度確認してください",
            color=discord.Color.red()
        )
        try:
            await user.send(embed=embed)
        except:
            pass
            
        if log_channel:
            log_embed = discord.Embed(
                title=f"❌ {user.mention} の認証申請を拒否しました",
                description=None,
                color=discord.Color.red()
            )
                
            log_embed.add_field(name="あなたの名前を入力してください", value=name, inline=False)
            log_embed.add_field(name="誰から招待されましたか？", value=inviter, inline=False)
            log_embed.add_field(name="管理者への一言(任意), value=message, inline=False)
            log_embed.set_footer(text=f"担当者: {interaction.user.mention}")
            
            await log_channel.send(embed=log_embed)

#認証チャンネル用Embedのボタン
class VerifyMainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="認証コード入力", style=discord.ButtonStyle.green)
    async def code_input(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CodeInputModal())
        
    @discord.ui.button(label="認証申請", style=discord.ButtonStyle.green)
    async def apply(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VerifyApplyModal())
        
#管理者チェック
def admin_only(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator
    
#未承認ロール付与&入室通知
@bot.event
async def on_member_join(member):
    settings = load_settings()
    unverified_role_id = settings["unverified_role"]
    
    if unverified_role_id:
        role = member.guild.get_role(unverified_role_id)
        if role:
            await member.add_roles(role)


#/verifyrole メンバーロール付与設定
@bot.tree.command(name="verifyrole", description="メンバーロールを設定")
@app_commands.check(admin_only)
async def verifyrole(interaction: discord.Interaction, role: discord.Role):
    settings = load_settings()
    settings["member_role"] = role.id
    save_settings(settings)
    
    await interaction.response.send_message(
        f"✅ メンバーロールを {role.mention} に設定しました。",
        ephemeral=True
    )

#/unverifiedrole 未認証ロール付与設定
@bot.tree.command(name="unverifiedrole", description="未認証ロールを設定")
@app_commands.check(admin_only)
async def unverifyrole(interaction: discord.Interaction, role: discord.Role):
    settings = load_settings()
    settings["unverified_role"] = role.id
    save_settings(settings)
    
    await interaction.response.send_message(
        f"✅ 未認証ロールを {role.mention} に設定しました。",
        ephemeral=True
    )

#/verifycode 認証コード設定
@bot.tree.command(name="verifycode", description="認証コードを設定")
@app_commands.check(admin_only)
async def verifycode(interaction: discord.Interaction, code: str):
    settings = load_settings()
    settings["verify_code"] = code
    save_settings(settings)
    
    await interaction.response.send_message(
        f"🔑 認証コードを **{code}** に設定しました",
        ephemeral=True
    )
    
#/verifyset 認証用Embed設置
@bot.tree.command(name="verifyset", description="認証用Embedを設置します")
@app_commands.check(admin_only)
async def verifyset(interaction: discord.Interaction):
    
    settings = load_settings()
    settings["verify_channel"] = interaction.channel.id
    save_settings(settings)
    
    verify_embed = discord.Embed(
        title="🔐 認証パネル",
        description=(
            "以下のボタンから認証を行ってください。\n"
            "・認証コードを持っている場合は **認証コード入力**\n"
            "・認証コードを持っていない場合は **認証申請**"
        ),
        color=discord.Color.orange()
    )
    
    await interaction.response.send_message(
        f"✅ このチャンネルに認証パネルを設置しました。",
        ephemeral=True
    )
    
    await interaction.channel.send(embed=verify_embed, view=VerifyMainView())

#/settings botの設定一覧表示
@bot.tree.command(name="settings", description="botの設定一覧を表示します")
@app_commands.check(admin_only)
async def settings(interaction: discord.Interaction):
    
    settings = load_settings()
    
    embed = discord.Embed(
        title="⚙️ botの設定一覧",
        description=None,
        color=discord.Color.blue()
    )
    
    verify_channel = settings.get("verify_channel")
    embed.add_field(
        name="🔐 認証チャンネル",
        value=f"<#{verify_channel}>" if verify_channel else "未設定",
        inline=False
    )
    member_role = settings.get("member_role")
    embed.add_field(
        name="✅ メンバーロール(認証済みロール),
        value=f"<@&{member_role}>" if member_role else "未設定",
        inline=False
    )
    unverified_role = settings.get("unverified_role")
    embed.add_field(
        name="🔒 未認証ロール",
        value=f"<@&{unverified_role}>" if unverified_role else "未設定",
        inline=False
    )
    verify_code = settings.get("verify_code")
    embed.add_field(
        name="🔑 認証コード",
        value=f"`{verify_code}`" if verify_code else "未設定",
        inline=False
    )
    apply_channel = settings.get("apply_channel")
    embed.add_field(
        name="📬 認証申請受信チャンネル",
        value=f"<#{apply_channel}>" if apply_channel else "未設定",
        inline=False
    )
    log_channel = settings.get("log_channel")
    embed.add_field(
        name="💻 認証ログチャンネル",
        value=f"<#{log_channel}>" if log_channel else "未設定",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

#ステータス切り替え
@tasks.loop(seconds=15)
async def presence_loop():
    if not hasattr(presence_loop, "toggle"):
        presence_loop.toggle = False
    presence_loop.toggle = not presence_loop.toggle
    if presence_loop.toggle:
        await bot.change_presence(
            activity=discord.Game("🔐 認証システム作動中･･･")
        )
    else:
        ping = round(bot.latency * 1000)
        await bot.change_presence(
            activity=discord.Game(f"Verify System┃Ping {ping}ms")
        )

#起動
@bot.event
async def on_ready():
    print(f"✅ ログイン完了: {bot.user}")
    await bot.tree.sync()
    print("✅ スラッシュコマンド同期完了")
    if not presence_loop.is_running():
        presence_loop.start()

bot.run(TOKEN)