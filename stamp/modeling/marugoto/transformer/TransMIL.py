"""
In parts from https://github.com/lucidrains/vit-pytorch/blob/main/vit_pytorch/vit.py
"""

# %%
import torch
from einops import repeat
from torch import nn


class FeedForward(nn.Module):
    def __init__(self, dim, hidden_dim, norm_layer=nn.LayerNorm, dropout=0.0):
        super().__init__()
        self.mlp = nn.Sequential(
            norm_layer(dim),
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.mlp(x)


class MultiHeadDiffAttention(nn.Module):
    def __init__(
        self, embed_dim: int, n_heads: int = 8, diff_weight_init: float = 0.2
    ) -> None:
        super().__init__()
        self.n_heads = n_heads
        self.q_proj = nn.Linear(embed_dim, embed_dim, bias=False)
        self.k_proj = nn.Linear(embed_dim, embed_dim, bias=False)
        self.v_proj = nn.Linear(embed_dim, embed_dim, bias=False)
        self.norm = nn.RMSNorm([n_heads, embed_dim // n_heads])
        self.o_proj = nn.Linear(embed_dim, embed_dim)

        # TODO parameterize this like in the paper?
        # But why???
        self.diff_weight = nn.Parameter(torch.tensor(diff_weight_init))

    def forward(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        # shape: [batch, seq_num, head, {0,1}, embedding]
        qs = self.q_proj(x).view(*x.shape[:-1], self.n_heads, 2, -1)
        ks = self.k_proj(x).view(*x.shape[:-1], self.n_heads, 2, -1)

        s = qs.size(-1) ** (-1 / 2)  # scaling factor for

        atts = torch.softmax(torch.einsum("bqhif,bkhif->ibhqk", qs, ks) * s, dim=-1)
        # shape: [batch, head, query, key]
        att = atts[0] - self.diff_weight * atts[1]

        vs = self.v_proj(x).view(*x.shape[:-1], self.n_heads, -1)
        # shape: [batch, seq_num, embed]
        concated = self.norm(torch.einsum("bhqk,bkhe->bqhe", att, vs)).reshape(
            *vs.shape[:-2], -1  # collapse heads and embeddings into one
        )

        return self.o_proj(concated) * (1 - self.diff_weight)


class Attention(nn.Module):
    def __init__(self, dim, heads=8, norm_layer=nn.LayerNorm, dropout=0.0) -> None:
        super().__init__()
        self.heads = heads
        self.norm = norm_layer(dim)
        self.mhsa = nn.MultiheadAttention(dim, heads, dropout, batch_first=True)

    def forward(self, x, mask=None):
        if mask is not None:
            mask = mask.repeat(self.heads, 1, 1)

        x = self.norm(x)
        attn_output, _ = self.mhsa(x, x, x, need_weights=False, attn_mask=mask)
        return attn_output


class Transformer(nn.Module):
    def __init__(
        self, dim, depth, heads, dim_head, mlp_dim, norm_layer=nn.LayerNorm, dropout=0.0
    ):
        super().__init__()
        self.depth = depth
        self.layers = nn.ModuleList([
            nn.ModuleList(
                [
                    # Attention(
                    #     dim,
                    #     heads=heads,
                    #     dim_head=dim_head,
                    #     norm_layer=norm_layer,
                    #     dropout=dropout,
                    # ),
                    MultiHeadDiffAttention(embed_dim=dim, n_heads=heads),
                    FeedForward(
                        dim, mlp_dim, norm_layer=norm_layer, dropout=dropout
                    ),
                ]
            )
            for _ in range(depth)
        ])
        self.norm = norm_layer(dim)

    def forward(self, x, mask=None):
        for attn, ff in self.layers:    # pyright: ignore[reportGeneralTypeIssues]
            x_attn = attn(x, mask=mask)
            x = x_attn + x
            x = ff(x) + x
        return self.norm(x)


class TransMIL(nn.Module):
    def __init__(
        self,
        *,
        num_classes: int,
        input_dim: int = 768,
        dim: int = 512,
        depth: int = 2,
        heads: int = 8,
        dim_head: int = 64,
        mlp_dim: int = 2048,
        dropout: float = 0.0,
        emb_dropout: float = 0.0,
    ):
        super().__init__()
        self.cls_token = nn.Parameter(torch.randn(dim))

        self.fc = nn.Sequential(nn.Linear(input_dim, dim, bias=True), nn.GELU())
        self.dropout = nn.Dropout(emb_dropout)

        self.transformer = Transformer(
            dim, depth, heads, dim_head, mlp_dim, nn.LayerNorm, dropout
        )

        self.mlp_head = nn.Sequential(nn.Linear(dim, num_classes))

    def forward(self, x, lens):
        # remove unnecessary padding
        # (deactivated for now, since the memory usage fluctuates more and is overall bigger)
        # x = x[:, :torch.max(lens)].contiguous()
        b, n, d = x.shape

        # map input sequence to latent space of TransMIL
        x = self.dropout(self.fc(x))

        cls_tokens = repeat(self.cls_token, "d -> b 1 d", b=b)
        x = torch.cat((cls_tokens, x), dim=1)
        lens = lens + 1  # account for cls token

        x = self.transformer(x)

        x = x[:, 0]  # only take class token

        return self.mlp_head(x)
