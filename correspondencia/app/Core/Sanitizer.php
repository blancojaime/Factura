<?php
declare(strict_types=1);
namespace App\Core;

/** Limpia HTML del editor mediante lista blanca de etiquetas y atributos. */
final class Sanitizer
{
    private const TAGS = ['p','br','strong','b','em','i','u','s','ul','ol','li','h1','h2','h3','h4','blockquote','span','a','div','hr','sub','sup','pre','table','thead','tbody','tr','td','th'];

    public static function html(string $html): string
    {
        $html = trim($html);
        if ($html === '') return '';
        $dom = new \DOMDocument();
        libxml_use_internal_errors(true);
        $dom->loadHTML('<?xml encoding="utf-8"?><div id="__root">' . $html . '</div>', LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD);
        libxml_clear_errors();
        $root = $dom->getElementById('__root');
        if (!$root) return e($html);
        self::limpiar($root);
        $out = '';
        foreach ($root->childNodes as $n) $out .= $dom->saveHTML($n);
        return $out;
    }

    private static function limpiar(\DOMNode $nodo): void
    {
        foreach (iterator_to_array($nodo->childNodes) as $h) {
            if ($h instanceof \DOMComment) { $nodo->removeChild($h); continue; }
            if (!$h instanceof \DOMElement) continue;
            $t = strtolower($h->tagName);
            if (!in_array($t, self::TAGS, true)) {
                if (in_array($t, ['script','style','iframe','object','embed','svg','math','form'], true)) { $nodo->removeChild($h); continue; }
                self::limpiar($h);
                while ($h->firstChild) $nodo->insertBefore($h->firstChild, $h);
                $nodo->removeChild($h);
                continue;
            }
            foreach (iterator_to_array($h->attributes) as $a) {
                $n = strtolower($a->name);
                $keep = false;
                if ($t === 'a' && $n === 'href' && preg_match('#^(https?://|mailto:)#i', trim($a->value))) $keep = true;
                if ($n === 'class') {
                    $cls = array_filter(explode(' ', $a->value), fn($c) => preg_match('/^ql-[\w-]+$/', $c));
                    if ($cls) { $h->setAttribute('class', implode(' ', $cls)); $keep = true; }
                }
                if (in_array($n, ['colspan', 'rowspan'], true) && ctype_digit($a->value)) $keep = true;
                if (!$keep) $h->removeAttribute($a->name);
            }
            if ($t === 'a') { $h->setAttribute('rel', 'noopener noreferrer'); $h->setAttribute('target', '_blank'); }
            self::limpiar($h);
        }
    }
}
