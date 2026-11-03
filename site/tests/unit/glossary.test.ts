import { test } from 'node:test';
import assert from 'node:assert/strict';
import { byLetter, definitions, termSlug, uniqueTerms } from '../../src/lib/glossary.ts';

const CHAPTER = `<p>Intro.</p>
<aside class="sk-block sk-definition" data-block="definition"><div class="sk-block-title">Before a heading</div><p>Early.</p></aside>
<h2 id="first">First</h2>
<aside class="sk-block sk-definition" data-block="definition"><div class="sk-block-title"><strong>Nonce</strong></div>
<p>A number used once.</p>
</aside>
<aside class="sk-block sk-note" data-block="note"><div class="sk-block-title">A note</div><p>Not a term.</p></aside>
<h2 id="second">Second</h2>
<aside class="sk-block sk-definition" data-block="definition"><div class="sk-block-title">Definition</div><p>No title of its own.</p></aside>
<aside class="sk-block sk-definition" data-block="definition"><div class="sk-block-title"><span class="katex">x</span> value</div><p>With math.</p></aside>`;

test('definitions come with their term and the section they stand in', () => {
  const found = definitions(CHAPTER);
  assert.deepEqual(
    found.map((d) => [d.term, d.heading]),
    [
      ['Before a heading', null],
      ['Nonce', 'first'],
      ['x value', 'second'],
    ],
  );
  assert.equal(found[1]?.html, '<p>A number used once.</p>');
  assert.equal(found[1]?.termHtml, '<strong>Nonce</strong>');
});

test('a box without its own title and other boxes are no terms', () => {
  assert.ok(!definitions(CHAPTER).some((d) => d.term === 'Definition' || d.term === 'A note'));
  assert.deepEqual(definitions('<p>Nothing here.</p>'), []);
});

test('terms sort by the language and group by their first letter', () => {
  const terms = ['Zebra', 'ähnlich', 'Apfel', '2-of-2 output', 'Öl'].map((term) => ({ term }));
  const groups = byLetter(terms, 'de');
  assert.deepEqual(groups.map(([letter]) => letter), ['#', 'A', 'O', 'Z']);
  assert.deepEqual(groups[1]?.[1].map((t) => t.term), ['ähnlich', 'Apfel']);
});

test('a term defined twice counts once, where it comes first', () => {
  const entries = [
    { term: 'Hash function', chapter: 1 },
    { term: 'Nonce', chapter: 2 },
    { term: 'hash function', chapter: 3 },
  ];
  assert.deepEqual(uniqueTerms(entries).map((e) => e.chapter), [1, 2]);
});

test('anchors are plain', () => {
  assert.equal(termSlug('Merkle tree'), 'term-merkle-tree');
  assert.equal(termSlug('Übergröße!'), 'term-ubergro-e');
  assert.equal(termSlug('∑'), 'term-x');
});
