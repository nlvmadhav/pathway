// Copyright © 2024 Pathway

use std::collections::HashMap;

use crate::helpers::ReplaceErrors;

use itertools::Itertools;
use pathway_engine::connectors::data_format::{
    InnerSchemaField, ParsedEvent, Parser, TransparentParser,
};
use pathway_engine::connectors::data_storage::{DataEventType, ReaderContext};
use pathway_engine::connectors::SessionType;
use pathway_engine::engine::{Type, Value};

#[test]
fn test_transparent_parser() -> eyre::Result<()> {
    let value_field_names = vec!["a".to_owned(), "b".to_owned()];
    let schema = [
        ("a".to_owned(), InnerSchemaField::new(Type::Int, None)),
        (
            "b".to_owned(),
            InnerSchemaField::new(Type::Optional(Type::String.into()), None),
        ),
    ];
    let mut parser =
        TransparentParser::new(None, value_field_names, schema.into(), SessionType::Native)?;
    let contexts = vec![
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([
                ("a".to_owned(), Ok(Value::Int(3))),
                ("b".to_owned(), Ok(Value::from("abc"))),
            ])
            .into(),
        ),
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([("b".to_owned(), Ok(Value::from("abc")))]).into(),
        ),
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([("a".to_owned(), Ok(Value::Int(2)))]).into(),
        ),
    ];
    let expected = vec![
        ParsedEvent::Insert((None, vec![Value::from(3), Value::from("abc")])),
        ParsedEvent::Insert((None, vec![Value::Error, Value::from("abc")])),
        ParsedEvent::Insert((None, vec![Value::from(2), Value::Error])),
    ];
    for (context_i, expected_i) in contexts.into_iter().zip_eq(expected) {
        assert_eq!(
            parser
                .parse(&context_i)
                .expect("creating message should not fail")
                .into_iter()
                .exactly_one()?
                .replace_errors(),
            expected_i
        );
    }
    Ok(())
}

#[test]
fn test_transparent_parser_defaults() -> eyre::Result<()> {
    let value_field_names = vec!["a".to_owned(), "b".to_owned()];
    let schema = [
        (
            "a".to_owned(),
            InnerSchemaField::new(Type::Int, Some(Value::Int(10))),
        ),
        (
            "b".to_owned(),
            InnerSchemaField::new(
                Type::Optional(Type::String.into()),
                Some(Value::from("default")),
            ),
        ),
    ];
    let mut parser =
        TransparentParser::new(None, value_field_names, schema.into(), SessionType::Native)?;
    let contexts = vec![
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([
                ("a".to_owned(), Ok(Value::Int(3))),
                ("b".to_owned(), Ok(Value::from("abc"))),
            ])
            .into(),
        ),
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([("b".to_owned(), Ok(Value::from("abc")))]).into(),
        ),
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([("a".to_owned(), Ok(Value::Int(2)))]).into(),
        ),
        ReaderContext::from_diff(
            DataEventType::Delete,
            None,
            HashMap::from([("a".to_owned(), Ok(Value::Int(2)))]).into(),
        ),
    ];
    let expected = vec![
        ParsedEvent::Insert((None, vec![Value::from(3), Value::from("abc")])),
        ParsedEvent::Insert((None, vec![Value::from(10), Value::from("abc")])),
        ParsedEvent::Insert((None, vec![Value::from(2), Value::from("default")])),
        ParsedEvent::Delete((None, vec![Value::from(2), Value::from("default")])),
    ];
    for (context_i, expected_i) in contexts.into_iter().zip_eq(expected) {
        assert_eq!(
            parser
                .parse(&context_i)
                .expect("creating message should not fail")
                .into_iter()
                .exactly_one()?
                .replace_errors(),
            expected_i
        );
    }
    Ok(())
}

#[test]
fn test_transparent_parser_upsert() -> eyre::Result<()> {
    let value_field_names = vec!["a".to_owned(), "b".to_owned()];
    let schema = [
        ("a".to_owned(), InnerSchemaField::new(Type::Int, None)),
        ("b".to_owned(), InnerSchemaField::new(Type::String, None)),
    ];
    let mut parser =
        TransparentParser::new(None, value_field_names, schema.into(), SessionType::Upsert)?;
    let contexts = vec![
        ReaderContext::from_diff(
            DataEventType::Insert,
            None,
            HashMap::from([
                ("a".to_owned(), Ok(Value::Int(3))),
                ("b".to_owned(), Ok(Value::from("abc"))),
            ])
            .into(),
        ),
        ReaderContext::from_diff(
            DataEventType::Delete,
            None,
            HashMap::from([
                ("a".to_owned(), Ok(Value::Int(3))),
                ("b".to_owned(), Ok(Value::from("abc"))),
            ])
            .into(),
        ),
    ];
    let expected = vec![
        ParsedEvent::Insert((None, vec![Value::from(3), Value::from("abc")])),
        ParsedEvent::Delete((None, vec![])),
    ];
    for (context_i, expected_i) in contexts.into_iter().zip_eq(expected) {
        assert_eq!(
            parser
                .parse(&context_i)
                .expect("creating message should not fail")
                .into_iter()
                .exactly_one()?
                .replace_errors(),
            expected_i
        );
    }
    Ok(())
}
