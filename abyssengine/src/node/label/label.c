/**
 * Copyright (C) 2021 Tim Sarbin
 * This file is part of AbyssEngine <https://github.com/AbyssEngine>.
 *
 * AbyssEngine is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * AbyssEngine is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with AbyssEngine.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "label.h"
#include "../../engine/engine.h"
#include <stdlib.h>

typedef struct label {
    node node;
    spritefont *font;
    char *caption;
    e_alignment horizontal_alignment;
    e_alignment vertical_alignment;
    e_blend_mode blend;
    rgb color_mod;
} label;

void label_render_callback(node *source, engine *e, int offset_x, int offset_y) {
    label *lbl = (label *)source;

    if (!source->visible || !source->active)
        return;

    int pos_x = source->x + offset_x;
    int pos_y = source->y + offset_y;

    int final_width;
    int final_height;
    spritefont_get_metrics(lbl->font, lbl->caption, &final_width, &final_height);

    switch (lbl->horizontal_alignment) {
    case alignment_middle:
        pos_x -= (final_width / 2);
        break;
    case alignment_end:
        pos_x -= final_width;
        break;
    default:
        break;
    }

    switch (lbl->vertical_alignment) {
    case alignment_middle:
        pos_y -= (final_height / 2);
        break;
    case alignment_end:
        pos_y -= final_height;
        break;
    default:
        break;
    }

    spritefont_draw_text(lbl->font, pos_x, pos_y, lbl->caption, lbl->blend, lbl->color_mod);

    node_default_render_callback(source, e, offset_x, offset_y);
}

label *label_create(spritefont *font) {
    label *result = calloc(1, sizeof(label));
    node_initialize(&result->node);
    result->font = font;
    result->blend = blend_mode_blend;
    result->color_mod.r = 0xFF;
    result->color_mod.g = 0xFF;
    result->color_mod.b = 0xFF;
    result->node.render_callback = label_render_callback;

    return result;
}

void label_destroy(label *source) {
    if (source->node.parent != NULL)
        node_remove(&source->node, engine_get_global_instance());

    if (source->caption != NULL)
        free(source->caption);

    free(source);
}

const char *label_get_text(const label *source) { return source->caption; }
void label_set_text(label *source, const char *text) {
    if (source->caption != NULL)
        free(source->caption);

    source->caption = strdup(text);
}

e_alignment label_get_horizontal_alignment(const label *label) { return label->horizontal_alignment; }

void label_set_horizontal_alignment(label *label, e_alignment alignment) { label->horizontal_alignment = alignment; }

e_alignment label_get_vertical_alignment(const label *label) { return label->vertical_alignment; }

void label_set_vertical_alignment(label *label, e_alignment alignment) { label->vertical_alignment = alignment; }

e_blend_mode label_get_blend_mode(const label *label) { return label->blend; }

void label_set_blend_mode(label *label, e_blend_mode blend_mode) { label->blend = blend_mode; }

rgb label_get_color_mod(const label *label) { return label->color_mod; }

void label_set_color_mod(label *label, rgb color_mod) { label->color_mod = color_mod; }
